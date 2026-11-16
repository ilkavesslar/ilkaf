from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from cv.frame import MOCK_SYNTHETIC_LABEL, Frame
from cv.identity import AnonymousIdentityMatcher
from cv.intelligence import (
    ActivityClass,
    EngineConfig,
    HumanIntelligenceEngine,
    Keypoint,
    KeypointName,
    PersonIntelligenceObservation,
    missing_keypoints,
)
from cv.observation import BoundingBox, Observation
from cv.pose.coco17 import PoseEstimate

START = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
STEP = 0.2
STANDING_BOX = (0.4, 0.2, 0.6, 0.95)
LYING_BOX = (0.2, 0.78, 0.7, 0.95)
SHAPE_ONLY = SimpleNamespace(shape=(480, 480, 3))


def _frame(index: int, data: object = SHAPE_ONLY, *, synthetic: bool = True) -> Frame:
    moment = START + timedelta(seconds=index * STEP)
    return Frame(
        data=data,
        index=index,
        captured_at=moment,
        processed_at=moment,
        source_id="rtsp:cam-a" if not synthetic else "file:demo.mp4",
        is_synthetic=synthetic,
        source_kind="file" if synthetic else "rtsp",
    )


def _person(
    box: tuple[float, float, float, float],
    *,
    camera_id: str | None = "cam-a",
    object_class: str = "person",
    synthetic: bool = True,
) -> Observation:
    return Observation(
        observation_id=uuid4(),
        source_id="file:demo.mp4",
        object_class=object_class,
        confidence=0.87,
        bounding_box=BoundingBox(*box),
        model_id="stub-detector",
        model_version="1",
        observed_at=START,
        camera_id=camera_id,
        is_synthetic=synthetic,
    )


def _pose(points: dict[KeypointName, tuple[float, float]]) -> PoseEstimate:
    keypoints = list(missing_keypoints())
    for name, (x_pos, y_pos) in points.items():
        keypoints[name] = Keypoint(x=x_pos, y=y_pos, confidence=0.9, visibility=0.9)
    return PoseEstimate(keypoints=tuple(keypoints))


UPRIGHT = _pose(
    {
        KeypointName.LEFT_SHOULDER: (0.45, 0.3),
        KeypointName.RIGHT_SHOULDER: (0.55, 0.3),
        KeypointName.LEFT_HIP: (0.46, 0.55),
        KeypointName.RIGHT_HIP: (0.54, 0.55),
        KeypointName.LEFT_KNEE: (0.46, 0.75),
        KeypointName.RIGHT_KNEE: (0.54, 0.75),
        KeypointName.LEFT_WRIST: (0.43, 0.55),
    }
)
LYING = _pose(
    {
        KeypointName.LEFT_SHOULDER: (0.3, 0.85),
        KeypointName.RIGHT_SHOULDER: (0.3, 0.87),
        KeypointName.LEFT_HIP: (0.55, 0.86),
        KeypointName.RIGHT_HIP: (0.55, 0.88),
    }
)


class _ScriptedPose:
    model_id = "stub-pose"
    model_version = "1"

    def __init__(self) -> None:
        self.next: list[PoseEstimate] = []

    @property
    def available(self) -> bool:
        return True

    def estimate(self, frame: Frame) -> list[PoseEstimate]:
        return list(self.next)


class _BrokenPose(_ScriptedPose):
    def estimate(self, frame: Frame) -> list[PoseEstimate]:
        raise RuntimeError("pose backend crashed")


def test_without_pose_keypoints_are_honestly_missing() -> None:
    engine = HumanIntelligenceEngine("cam-a")
    first = engine.process_frame(_frame(0), [_person(STANDING_BOX)])
    second = engine.process_frame(_frame(1), [_person(STANDING_BOX)])
    record = first[0]
    assert record.tracking_status == "tentative"
    assert record.global_person_id is None
    assert all(kp.x is None and kp.visibility == 0.0 for kp in record.keypoints)
    assert record.activity_class is ActivityClass.UNKNOWN
    assert record.activity_confidence == 0.0
    assert second[0].tracking_status == "active"
    assert second[0].global_person_id is not None
    assert second[0].local_track_id == "cam-a:t1"
    assert second[0].model_versions["pose"] == "none@0"
    assert second[0].model_versions["detector"] == "stub-detector@1"
    assert set(second[0].model_versions) == {"detector", "tracker", "pose", "activity", "identity"}


def test_filters_non_person_and_foreign_camera_observations() -> None:
    engine = HumanIntelligenceEngine("cam-a")
    results = engine.process_frame(
        _frame(0),
        [
            _person(STANDING_BOX, object_class="forklift"),
            _person(STANDING_BOX, camera_id="cam-b"),
        ],
    )
    assert results == []


def test_empty_frame_ages_tracks_and_drops_tentative() -> None:
    engine = HumanIntelligenceEngine("cam-a")
    engine.process_frame(_frame(0), [_person(STANDING_BOX)])
    assert engine.process_frame(_frame(1), []) == []
    assert engine.tracker.tracks == []


def test_pose_failure_degrades_to_missing_keypoints() -> None:
    engine = HumanIntelligenceEngine("cam-a", pose_estimator=_BrokenPose())
    results = engine.process_frame(_frame(0), [_person(STANDING_BOX)])
    assert len(results) == 1
    assert all(not kp.observed for kp in results[0].keypoints)


def test_pose_keypoints_drive_standing_activity() -> None:
    pose = _ScriptedPose()
    pose.next = [UPRIGHT]
    engine = HumanIntelligenceEngine("cam-a", pose_estimator=pose)
    results = [engine.process_frame(_frame(i), [_person(STANDING_BOX)])[0] for i in range(8)]
    last = results[-1]
    assert last.keypoints[KeypointName.LEFT_SHOULDER].x == pytest.approx(0.45)
    assert last.activity_class is ActivityClass.STANDING
    assert last.activity_started_at is not None
    assert last.model_versions["pose"] == "stub-pose@1"


def test_end_to_end_fall_then_person_down() -> None:
    pose = _ScriptedPose()
    engine = HumanIntelligenceEngine("cam-a", pose_estimator=pose)
    classes: list[ActivityClass] = []
    for i in range(30):
        down = i >= 8
        pose.next = [LYING if down else UPRIGHT]
        box = LYING_BOX if down else STANDING_BOX
        classes.append(engine.process_frame(_frame(i), [_person(box)])[0].activity_class)
    assert classes[8] is not ActivityClass.FALLING
    assert ActivityClass.FALLING in classes
    assert classes[-1] is ActivityClass.PERSON_DOWN
    assert classes.index(ActivityClass.FALLING) < classes.index(ActivityClass.PERSON_DOWN)


def test_reentry_on_same_camera_keeps_global_person_id() -> None:
    size = 40
    image = [
        [(0, 0, 220) if y < size // 2 else (220, 0, 0) for _x in range(size)] for y in range(size)
    ]
    engine = HumanIntelligenceEngine("cam-a", identity_matcher=AnonymousIdentityMatcher())
    box = (0.3, 0.1, 0.7, 0.9)
    first = [engine.process_frame(_frame(i, image), [_person(box)]) for i in range(3)]
    for i in range(3, 7):
        engine.process_frame(_frame(i, image), [])
    second = [engine.process_frame(_frame(i, image), [_person(box)]) for i in range(7, 10)]
    assert first[-1][0].local_track_id != second[-1][0].local_track_id
    assert first[-1][0].global_person_id == second[-1][0].global_person_id


def test_lost_tracks_emitted_only_when_configured() -> None:
    engine = HumanIntelligenceEngine("cam-a", config=EngineConfig(emit_lost_tracks=True))
    engine.process_frame(_frame(0), [_person(STANDING_BOX)])
    engine.process_frame(_frame(1), [_person(STANDING_BOX)])
    lost = engine.process_frame(_frame(2), [])
    assert [record.tracking_status for record in lost] == ["lost"]
    assert lost[0].activity_class is ActivityClass.UNKNOWN
    quiet = HumanIntelligenceEngine("cam-a")
    quiet.process_frame(_frame(0), [_person(STANDING_BOX)])
    quiet.process_frame(_frame(1), [_person(STANDING_BOX)])
    assert quiet.process_frame(_frame(2), []) == []


def test_synthetic_flags_propagate_and_records_round_trip() -> None:
    engine = HumanIntelligenceEngine("cam-a")
    synthetic = engine.process_frame(_frame(0), [_person(STANDING_BOX)])[0]
    assert synthetic.is_synthetic is True
    assert synthetic.mock_label == MOCK_SYNTHETIC_LABEL
    assert PersonIntelligenceObservation.from_dict(synthetic.to_dict()) == synthetic

    live = HumanIntelligenceEngine("cam-a")
    real = live.process_frame(_frame(0, synthetic=False), [_person(STANDING_BOX, synthetic=False)])[
        0
    ]
    assert real.is_synthetic is False
    assert real.mock_label == ""
    mixed = HumanIntelligenceEngine("cam-a").process_frame(
        _frame(0, synthetic=False), [_person(STANDING_BOX, synthetic=True)]
    )[0]
    assert mixed.is_synthetic is True
    assert mixed.mock_label == MOCK_SYNTHETIC_LABEL
