from __future__ import annotations

from cv.intelligence.contract import Keypoint
from cv.observation import BoundingBox
from cv.pose.coco17 import PoseEstimate, associate_poses
from cv.pose.torchvision_keypoint import _to_keypoint


def test_to_keypoint_normalizes_and_rejects_low_score() -> None:
    joint = _to_keypoint(100.0, 50.0, 0.9, 200, 100, 0.2)
    assert joint.observed
    assert joint.x == 0.5
    assert joint.y == 0.5
    assert _to_keypoint(10.0, 10.0, 0.05, 100, 100, 0.2).observed is False
    assert _to_keypoint(-5.0, 10.0, 0.9, 100, 100, 0.2).observed is False


def test_associate_pose_to_matching_box() -> None:
    joints = [Keypoint.missing() for _ in range(17)]
    joints[5] = Keypoint(0.25, 0.3, 0.9, 0.9)
    joints[6] = Keypoint(0.35, 0.3, 0.9, 0.9)
    pose = PoseEstimate(keypoints=tuple(joints))
    assigned = associate_poses(
        [
            ("cam:t1", BoundingBox(0.1, 0.1, 0.5, 0.9)),
            ("cam:t2", BoundingBox(0.6, 0.1, 0.9, 0.9)),
        ],
        [pose],
    )
    assert list(assigned.keys()) == ["cam:t1"]
