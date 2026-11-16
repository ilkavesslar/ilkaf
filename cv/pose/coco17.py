"""COCO-17 pose records and pose-to-track association. Anonymous; not biometrics."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from cv.frame import Frame
from cv.gestures import PoseCue, associate_cues
from cv.intelligence.contract import (
    KEYPOINT_COUNT,
    Keypoint,
    KeypointName,
    missing_keypoints,
)
from cv.observation import BoundingBox

COCO_17_NAMES: tuple[str, ...] = tuple(name.name.lower() for name in KeypointName)

Point = tuple[float, float]


@dataclass(frozen=True, slots=True)
class PoseEstimate:
    """One person's 17 joints, before it is assigned to any track."""

    keypoints: tuple[Keypoint, ...]

    def __post_init__(self) -> None:
        if len(self.keypoints) != KEYPOINT_COUNT:
            raise ValueError(f"pose must contain {KEYPOINT_COUNT} keypoints")

    def point(self, name: KeypointName) -> Point | None:
        keypoint = self.keypoints[name]
        if not keypoint.observed or keypoint.x is None or keypoint.y is None:
            return None
        return (keypoint.x, keypoint.y)

    @property
    def observed_count(self) -> int:
        return sum(1 for keypoint in self.keypoints if keypoint.observed)

    @property
    def mean_confidence(self) -> float:
        observed = [keypoint.confidence for keypoint in self.keypoints if keypoint.observed]
        return sum(observed) / len(observed) if observed else 0.0

    def anchor(self) -> Point | None:
        """Shoulder midpoint, else hip midpoint, else ``None``. Never guessed."""

        for left, right in (
            (KeypointName.LEFT_SHOULDER, KeypointName.RIGHT_SHOULDER),
            (KeypointName.LEFT_HIP, KeypointName.RIGHT_HIP),
        ):
            mid = midpoint(self.point(left), self.point(right))
            if mid is not None:
                return mid
        return None


def midpoint(left: Point | None, right: Point | None) -> Point | None:
    if left is None or right is None:
        return None
    return ((left[0] + right[0]) / 2, (left[1] + right[1]) / 2)


def unobserved_pose() -> PoseEstimate:
    return PoseEstimate(keypoints=missing_keypoints())


@runtime_checkable
class PoseEstimator(Protocol):
    model_id: str
    model_version: str

    @property
    def available(self) -> bool: ...

    def estimate(self, frame: Frame) -> list[PoseEstimate]: ...


class NullPoseEstimator:
    """No pose model. Every track gets 17 joints with ``visibility=0``."""

    model_id = "none"
    model_version = "0"

    @property
    def available(self) -> bool:
        return False

    def estimate(self, frame: Frame) -> list[PoseEstimate]:
        return []


def associate_poses(
    tracks: Sequence[tuple[str, BoundingBox]],
    poses: Sequence[PoseEstimate],
) -> dict[str, PoseEstimate]:
    """Give each pose to the tightest track box containing its torso anchor.

    Delegates to ``cv.gestures.associate_cues``. Poses without an anchor are
    left unassigned rather than guessed onto a box.
    """

    indexed = [(index, box) for index, (_track_id, box) in enumerate(tracks)]
    cues: list[PoseCue] = []
    owners: list[PoseEstimate] = []
    for pose in poses:
        anchor = pose.anchor()
        if anchor is None:
            continue
        cues.append(
            PoseCue(
                anchor=anchor,
                left_wrist=pose.point(KeypointName.LEFT_WRIST),
                right_wrist=pose.point(KeypointName.RIGHT_WRIST),
            )
        )
        owners.append(pose)
    assigned = associate_cues(indexed, cues)
    result: dict[str, PoseEstimate] = {}
    for track_index, cue in assigned.items():
        owner = next(owners[i] for i, candidate in enumerate(cues) if candidate is cue)
        result[tracks[track_index][0]] = owner
    return result
