"""Optional MediaPipe Pose (33 landmarks) mapped to COCO-17. Off when the model is absent.

Landmarks below ``min_visibility`` or outside the image are reported as
unobserved (``visibility=0``, no coordinates) instead of being clamped.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from math import isfinite
from pathlib import Path
from typing import Any

from cv.frame import Frame
from cv.intelligence.contract import Keypoint, KeypointName
from cv.pose.coco17 import PoseEstimate

LOGGER = logging.getLogger(__name__)
MODEL_ID = "mediapipe-pose-landmarker"
MEDIAPIPE_LANDMARK_COUNT = 33
DEFAULT_MIN_VISIBILITY = 0.5

MEDIAPIPE_TO_COCO17: dict[KeypointName, int] = {
    KeypointName.NOSE: 0,
    KeypointName.LEFT_EYE: 2,
    KeypointName.RIGHT_EYE: 5,
    KeypointName.LEFT_EAR: 7,
    KeypointName.RIGHT_EAR: 8,
    KeypointName.LEFT_SHOULDER: 11,
    KeypointName.RIGHT_SHOULDER: 12,
    KeypointName.LEFT_ELBOW: 13,
    KeypointName.RIGHT_ELBOW: 14,
    KeypointName.LEFT_WRIST: 15,
    KeypointName.RIGHT_WRIST: 16,
    KeypointName.LEFT_HIP: 23,
    KeypointName.RIGHT_HIP: 24,
    KeypointName.LEFT_KNEE: 25,
    KeypointName.RIGHT_KNEE: 26,
    KeypointName.LEFT_ANKLE: 27,
    KeypointName.RIGHT_ANKLE: 28,
}


def _score(landmark: object, name: str) -> float | None:
    value = getattr(landmark, name, None)
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(number):
        return None
    return min(max(number, 0.0), 1.0)


def _keypoint(landmark: object, min_visibility: float) -> Keypoint:
    visibility = _score(landmark, "visibility")
    presence = _score(landmark, "presence")
    if visibility is None or visibility < min_visibility:
        return Keypoint.missing()
    try:
        x_pos = float(getattr(landmark, "x"))
        y_pos = float(getattr(landmark, "y"))
    except (AttributeError, TypeError, ValueError):
        return Keypoint.missing()
    if not (isfinite(x_pos) and isfinite(y_pos)) or not (
        0.0 <= x_pos <= 1.0 and 0.0 <= y_pos <= 1.0
    ):
        return Keypoint.missing()
    confidence = presence if presence is not None else visibility
    return Keypoint(x=x_pos, y=y_pos, confidence=confidence, visibility=visibility)


def landmarks_to_coco17(
    landmarks: Sequence[object],
    *,
    min_visibility: float = DEFAULT_MIN_VISIBILITY,
) -> PoseEstimate | None:
    """Map one MediaPipe 33-landmark pose to COCO-17, or ``None`` if malformed."""

    if len(landmarks) < MEDIAPIPE_LANDMARK_COUNT:
        return None
    keypoints = tuple(
        _keypoint(landmarks[MEDIAPIPE_TO_COCO17[name]], min_visibility) for name in KeypointName
    )
    return PoseEstimate(keypoints=keypoints)


def _rgb(image: object) -> Any | None:
    shape = getattr(image, "shape", None)
    if shape is None or len(shape) < 3 or int(shape[2]) < 3:
        return None
    try:
        import numpy as np
    except ImportError:
        return None
    array = np.asarray(image)
    if array.dtype != np.uint8:
        return None
    return np.ascontiguousarray(array[:, :, :3][:, :, ::-1])


class MediaPipePoseEstimator:
    """CPU MediaPipe PoseLandmarker from a local ``.task`` file. Never downloads."""

    model_id = MODEL_ID

    def __init__(
        self,
        model_path: Path,
        *,
        num_poses: int = 4,
        min_visibility: float = DEFAULT_MIN_VISIBILITY,
    ) -> None:
        if num_poses < 1:
            raise ValueError("num_poses must be >= 1")
        self._path = model_path
        self._num_poses = num_poses
        self._min_visibility = min_visibility
        self._landmarker: Any | None = None
        self.model_version = f"local:{model_path.name}"

    @property
    def available(self) -> bool:
        return self._landmarker is not None

    def open(self) -> bool:
        if self._landmarker is not None:
            return True
        if not self._path.is_file():
            LOGGER.info("pose model file missing; pose disabled", extra={"component": "cv.pose"})
            return False
        try:
            from mediapipe.tasks.python.core.base_options import BaseOptions
            from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions

            options = PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(self._path)),
                num_poses=self._num_poses,
            )
            self._landmarker = PoseLandmarker.create_from_options(options)
        except Exception:
            LOGGER.warning(
                "pose model could not be opened; pose disabled",
                exc_info=True,
                extra={"component": "cv.pose"},
            )
            self._landmarker = None
            return False
        return True

    def estimate(self, frame: Frame) -> list[PoseEstimate]:
        if self._landmarker is None:
            return []
        rgb = _rgb(frame.data)
        if rgb is None:
            return []
        try:
            import mediapipe as mp

            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self._landmarker.detect(image)
        except Exception:
            LOGGER.warning(
                "pose inference failed for frame",
                exc_info=True,
                extra={"component": "cv.pose", "frame_index": frame.index},
            )
            return []
        poses: list[PoseEstimate] = []
        for landmarks in getattr(result, "pose_landmarks", None) or []:
            pose = landmarks_to_coco17(landmarks, min_visibility=self._min_visibility)
            if pose is not None:
                poses.append(pose)
        return poses

    def close(self) -> None:
        landmarker = self._landmarker
        self._landmarker = None
        close = getattr(landmarker, "close", None)
        if callable(close):
            close()
