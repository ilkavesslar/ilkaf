"""ILKA computer-vision ingest package.

Sprint 3 M1 provides a file-based video source and a bounded frame buffer.
Sprint 3 M2 provides the typed observation contract (not incidents).
Sprint 3 M3 provides an optional CPU person detector (PROVISIONAL lab adapter).
Sprint 3 M4 is a PROVISIONAL lab CLI
(``scripts/dev/preview_person_detection.py``), not a backend or HTTP CV API.
Sprint 3 M5 is quality/tests and isolated FileSource smoke (lab only).
``RtspSource`` is a provisional RTSP adapter (timeouts, bounded reconnect).
It is not production camera integration, ONVIF, tracking, or an incident path.
``WebcamSource`` is a dev-only laptop camera. Its frames stay
``[MOCK / SYNTHETIC]``.

File frames from this package default to ``[MOCK / SYNTHETIC]``. RTSP frames
are non-synthetic. Construction of other non-synthetic labels stays available
so the two flags cannot contradict each other.
"""

from cv.detectors.base import PersonDetector
from cv.detectors.person_cpu import CpuPersonDetector
from cv.errors import (
    CvDependencyError,
    DetectorDependencyError,
    DetectorError,
    DetectorInferenceError,
    DetectorModelError,
    VideoDecodeError,
    VideoSourceError,
)
from cv.frame import MOCK_SYNTHETIC_LABEL, Frame, normalize_mock_label
from cv.observation import BoundingBox, Observation
from cv.streams.base import VideoSource
from cv.streams.buffer import BoundedFrameBuffer
from cv.streams.file import FileSource
from cv.streams.rtsp import RtspSource
from cv.streams.webcam import WebcamSource

__all__ = [
    "MOCK_SYNTHETIC_LABEL",
    "BoundedFrameBuffer",
    "BoundingBox",
    "CpuPersonDetector",
    "CvDependencyError",
    "DetectorDependencyError",
    "DetectorError",
    "DetectorInferenceError",
    "DetectorModelError",
    "FileSource",
    "Frame",
    "Observation",
    "PersonDetector",
    "RtspSource",
    "VideoDecodeError",
    "VideoSource",
    "VideoSourceError",
    "WebcamSource",
    "normalize_mock_label",
]
