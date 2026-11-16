from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from cv.intelligence.contract import (
    ActivityClass,
    PersonIntelligenceObservation,
    missing_keypoints,
)
from cv.intelligence.overlay import (
    SKELETON_EDGES,
    count_valid_poses,
    person_caption,
    pixel_xy,
    pixel_xyxy,
)
from cv.intelligence.contract import Keypoint
from cv.observation import BoundingBox


def _obs(*, keypoints=None, activity=ActivityClass.WALKING, conf=0.7) -> PersonIntelligenceObservation:
    return PersonIntelligenceObservation(
        observation_id=uuid4(),
        camera_id="webcam:0",
        source_id="webcam:0",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        local_track_id="webcam:0:t1",
        bbox=BoundingBox(0.2, 0.1, 0.5, 0.9),
        detection_confidence=0.91,
        keypoints=keypoints or missing_keypoints(),
        activity_class=activity,
        activity_confidence=0.0 if activity is ActivityClass.UNKNOWN else conf,
        movement_state="moving",
        tracking_status="active",
        model_versions={"detector": "ssdlite"},
        is_synthetic=True,
    )


def test_pixel_mapping_and_skeleton_edge_count() -> None:
    assert pixel_xyxy(BoundingBox(0.1, 0.2, 0.4, 0.8), 1000, 500) == (100, 100, 400, 400)
    assert pixel_xy(0.5, 0.25, 200, 100) == (100, 25)
    assert len(SKELETON_EDGES) >= 12


def test_count_valid_poses_requires_observed_joints() -> None:
    empty = _obs()
    assert count_valid_poses([empty]) == 0
    joints = list(missing_keypoints())
    joints[5] = Keypoint(0.3, 0.3, 0.9, 0.9)
    joints[6] = Keypoint(0.4, 0.3, 0.9, 0.9)
    joints[11] = Keypoint(0.3, 0.6, 0.9, 0.9)
    assert count_valid_poses([_obs(keypoints=tuple(joints))]) == 1


def test_person_caption_includes_track_and_activity() -> None:
    text = person_caption(_obs())
    assert "t1" in text
    assert "walking" in text
    assert "det 91%" in text
    unknown = person_caption(_obs(activity=ActivityClass.UNKNOWN, conf=0.0))
    assert "activity unknown" in unknown
