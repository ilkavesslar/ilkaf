"""Optional OpenCV import. The FastAPI backend does not require this module."""

from __future__ import annotations

from types import ModuleType

from cv.errors import CvDependencyError


def load_cv2() -> ModuleType:
    try:
        import cv2
    except ImportError as exc:
        raise CvDependencyError(
            "OpenCV is required for video ingest. Install the optional extra "
            "`opencv-python-headless` (not a backend runtime dependency)."
        ) from exc
    return cv2
