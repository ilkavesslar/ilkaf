"""Optional MediaPipe pose wrists. Waving stays off when the model is absent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cv.gestures import PoseCue

LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_WRIST = 15
RIGHT_WRIST = 16
_MIN_VISIBILITY = 0.5


class WristPoseReader:
    """Read anonymous wrist points. Does not detect people or assign track ids."""

    def __init__(self, model_path: Path) -> None:
        self._path = model_path
        self._landmarker: Any | None = None
        self.available = False

    def open(self) -> bool:
        if self._landmarker is not None:
            self.available = True
            return True
        if not self._path.is_file():
            return False
        try:
            from mediapipe.tasks.python.core.base_options import BaseOptions
            from mediapipe.tasks.python.vision import (
                PoseLandmarker,
                PoseLandmarkerOptions,
            )

            options = PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(self._path)),
                num_poses=2,
            )
            self._landmarker = PoseLandmarker.create_from_options(options)
        except Exception:  # noqa: BLE001
            self._landmarker = None
            self.available = False
            return False
        self.available = True
        return True

    def read(self, bgr_image: object) -> list[PoseCue]:
        if self._landmarker is None:
            return []
        rgb = _rgb(bgr_image)
        if rgb is None:
            return []
        try:
            import mediapipe as mp

            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self._landmarker.detect(image)
        except Exception:  # noqa: BLE001
            return []
        cues: list[PoseCue] = []
        for landmarks in getattr(result, "pose_landmarks", []) or []:
            cue = _cue(landmarks)
            if cue is not None:
                cues.append(cue)
        return cues

    def close(self) -> None:
        landmarker = self._landmarker
        self._landmarker = None
        self.available = False
        if landmarker is not None:
            close = getattr(landmarker, "close", None)
            if callable(close):
                close()


def _rgb(image: object) -> object | None:
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
    rgb = np.ascontiguousarray(array[:, :, :3][:, :, ::-1])
    return rgb


def _point(landmarks: list[object], index: int) -> tuple[float, float] | None:
    if index >= len(landmarks):
        return None
    landmark = landmarks[index]
    visibility = getattr(landmark, "visibility", None)
    if visibility is not None and float(visibility) < _MIN_VISIBILITY:
        return None
    return (float(landmark.x), float(landmark.y))


def _cue(landmarks: list[object]) -> PoseCue | None:
    left_shoulder = _point(landmarks, LEFT_SHOULDER)
    right_shoulder = _point(landmarks, RIGHT_SHOULDER)
    if left_shoulder is None or right_shoulder is None:
        return None
    anchor = (
        (left_shoulder[0] + right_shoulder[0]) / 2,
        (left_shoulder[1] + right_shoulder[1]) / 2,
    )
    return PoseCue(
        anchor=anchor,
        left_wrist=_point(landmarks, LEFT_WRIST),
        right_wrist=_point(landmarks, RIGHT_WRIST),
    )
