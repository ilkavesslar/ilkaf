from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from cv.frame import Frame
from cv.intelligence.contract import Keypoint, KeypointName, missing_keypoints
from cv.observation import BoundingBox
from cv.pose import (
    COCO_17_NAMES,
    MEDIAPIPE_TO_COCO17,
    MediaPipePoseEstimator,
    NullPoseEstimator,
    PoseEstimate,
    associate_poses,
    landmarks_to_coco17,
    unobserved_pose,
)

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def _pose(points: dict[KeypointName, tuple[float, float]]) -> PoseEstimate:
    keypoints = list(missing_keypoints())
    for name, (x_pos, y_pos) in points.items():
        keypoints[name] = Keypoint(x=x_pos, y=y_pos, confidence=0.9, visibility=0.9)
    return PoseEstimate(keypoints=tuple(keypoints))


def _landmarks(visibility: float = 0.9) -> list[SimpleNamespace]:
    return [
        SimpleNamespace(x=0.01 * index, y=0.02 * index, visibility=visibility, presence=0.8)
        for index in range(33)
    ]


def test_coco17_names_in_order() -> None:
    assert len(COCO_17_NAMES) == 17
    assert COCO_17_NAMES[0] == "nose"
    assert COCO_17_NAMES[5] == "left_shoulder"
    assert COCO_17_NAMES[16] == "right_ankle"


def test_mediapipe_mapping_covers_all_coco_joints() -> None:
    assert set(MEDIAPIPE_TO_COCO17) == set(KeypointName)
    assert MEDIAPIPE_TO_COCO17[KeypointName.LEFT_SHOULDER] == 11
    assert MEDIAPIPE_TO_COCO17[KeypointName.RIGHT_HIP] == 24
    assert MEDIAPIPE_TO_COCO17[KeypointName.LEFT_ANKLE] == 27
    assert len(set(MEDIAPIPE_TO_COCO17.values())) == 17


def test_landmarks_map_to_coco_positions() -> None:
    pose = landmarks_to_coco17(_landmarks())
    assert pose is not None
    shoulder = pose.keypoints[KeypointName.LEFT_SHOULDER]
    assert shoulder.x == pytest.approx(0.11)
    assert shoulder.y == pytest.approx(0.22)
    assert shoulder.confidence == pytest.approx(0.8)
    assert shoulder.visibility == pytest.approx(0.9)


def test_low_visibility_landmarks_are_missing_not_guessed() -> None:
    pose = landmarks_to_coco17(_landmarks(visibility=0.2))
    assert pose is not None
    assert all(kp.x is None and kp.visibility == 0.0 for kp in pose.keypoints)


def test_out_of_frame_landmarks_are_missing_not_clamped() -> None:
    landmarks = _landmarks()
    landmarks[0] = SimpleNamespace(x=-0.1, y=0.5, visibility=0.99, presence=0.99)
    pose = landmarks_to_coco17(landmarks)
    assert pose is not None
    assert pose.keypoints[KeypointName.NOSE].x is None


def test_short_landmark_list_is_rejected() -> None:
    assert landmarks_to_coco17(_landmarks()[:20]) is None


def test_unobserved_pose_is_honest() -> None:
    pose = unobserved_pose()
    assert pose.observed_count == 0
    assert pose.anchor() is None
    assert pose.mean_confidence == 0.0


def test_anchor_prefers_shoulders_then_hips() -> None:
    shoulders = _pose(
        {KeypointName.LEFT_SHOULDER: (0.4, 0.3), KeypointName.RIGHT_SHOULDER: (0.6, 0.3)}
    )
    assert shoulders.anchor() == pytest.approx((0.5, 0.3))
    hips = _pose({KeypointName.LEFT_HIP: (0.4, 0.6), KeypointName.RIGHT_HIP: (0.5, 0.6)})
    assert hips.anchor() == pytest.approx((0.45, 0.6))


def test_associate_poses_to_tightest_containing_box() -> None:
    pose = _pose({KeypointName.LEFT_SHOULDER: (0.3, 0.4), KeypointName.RIGHT_SHOULDER: (0.4, 0.4)})
    tracks = [
        ("cam-a:t1", BoundingBox(0.0, 0.0, 1.0, 1.0)),
        ("cam-a:t2", BoundingBox(0.2, 0.2, 0.5, 0.9)),
    ]
    assigned = associate_poses(tracks, [pose])
    assert list(assigned) == ["cam-a:t2"]
    assert assigned["cam-a:t2"] is pose


def test_pose_without_anchor_is_not_assigned() -> None:
    nose_only = _pose({KeypointName.NOSE: (0.3, 0.3)})
    assigned = associate_poses([("cam-a:t1", BoundingBox(0.0, 0.0, 1.0, 1.0))], [nose_only])
    assert assigned == {}


def test_two_poses_two_tracks() -> None:
    left = _pose({KeypointName.LEFT_SHOULDER: (0.1, 0.4), KeypointName.RIGHT_SHOULDER: (0.2, 0.4)})
    right = _pose({KeypointName.LEFT_SHOULDER: (0.7, 0.4), KeypointName.RIGHT_SHOULDER: (0.8, 0.4)})
    tracks = [
        ("cam-a:t1", BoundingBox(0.0, 0.2, 0.3, 0.9)),
        ("cam-a:t2", BoundingBox(0.6, 0.2, 0.9, 0.9)),
    ]
    assigned = associate_poses(tracks, [right, left])
    assert assigned["cam-a:t1"] is left
    assert assigned["cam-a:t2"] is right


def test_null_estimator_reports_unavailable() -> None:
    estimator = NullPoseEstimator()
    frame = Frame(data=b"", index=0, captured_at=NOW, processed_at=NOW, source_id="file:x")
    assert estimator.available is False
    assert estimator.estimate(frame) == []


def test_mediapipe_estimator_off_when_model_missing(tmp_path: Path) -> None:
    estimator = MediaPipePoseEstimator(tmp_path / "missing.task")
    assert estimator.open() is False
    assert estimator.available is False
    frame = Frame(data=b"", index=0, captured_at=NOW, processed_at=NOW, source_id="file:x")
    assert estimator.estimate(frame) == []
