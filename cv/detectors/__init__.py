"""Optional CPU person detector (Sprint 3 M3). Not incidents or live cameras."""

from cv.detectors.base import PersonDetector
from cv.detectors.mapping import (
    COCO_PERSON_LABEL,
    PERSON_CLASS,
    detections_to_observations,
    normalize_pixel_box,
)
from cv.detectors.person_cpu import CpuPersonDetector

__all__ = [
    "COCO_PERSON_LABEL",
    "PERSON_CLASS",
    "CpuPersonDetector",
    "PersonDetector",
    "detections_to_observations",
    "normalize_pixel_box",
]
