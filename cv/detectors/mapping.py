"""Pixel detections → M2 observations. No Torch or OpenCV imports."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from math import isfinite
from uuid import uuid4

from cv.frame import Frame
from cv.observation import BoundingBox, Observation

COCO_PERSON_LABEL = 1
PERSON_CLASS = "person"


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    number = float(value)
    if not isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def is_person_label(label: object) -> bool:
    """COCO person id is the integer 1. Floats and booleans are not class ids."""
    if type(label) is int:
        return label == COCO_PERSON_LABEL
    if isinstance(label, str):
        return label.strip().lower() == PERSON_CLASS
    return False


def normalize_pixel_box(
    x_min: object,
    y_min: object,
    x_max: object,
    y_max: object,
    *,
    width: int,
    height: int,
) -> BoundingBox | None:
    """Convert pixel xyxy to a clipped normalized box, or ``None`` if empty."""

    if width < 1 or height < 1:
        raise ValueError("frame width and height must be at least 1")
    try:
        left = _finite(x_min, "x_min")
        top = _finite(y_min, "y_min")
        right = _finite(x_max, "x_max")
        bottom = _finite(y_max, "y_max")
    except (TypeError, ValueError):
        return None
    nx_min = min(max(left / width, 0.0), 1.0)
    ny_min = min(max(top / height, 0.0), 1.0)
    nx_max = min(max(right / width, 0.0), 1.0)
    ny_max = min(max(bottom / height, 0.0), 1.0)
    if nx_max <= nx_min or ny_max <= ny_min:
        return None
    return BoundingBox(x_min=nx_min, y_min=ny_min, x_max=nx_max, y_max=ny_max)


def detections_to_observations(
    *,
    boxes: Sequence[Sequence[object]],
    labels: Sequence[object],
    scores: Sequence[object],
    frame: Frame,
    width: int,
    height: int,
    min_confidence: float,
    model_id: str,
    model_version: str,
    camera_id: str | None = None,
    observed_at: datetime | None = None,
) -> list[Observation]:
    """Map raw detector rows to M2 observations. Not an incident stage."""

    if not len(boxes) == len(labels) == len(scores):
        raise ValueError("boxes, labels, and scores must have the same length")
    min_confidence = _finite(min_confidence, "min_confidence")
    if min_confidence < 0.0 or min_confidence > 1.0:
        raise ValueError("min_confidence must be in [0.0, 1.0]")
    stamped = observed_at if observed_at is not None else datetime.now(UTC)
    observations: list[Observation] = []
    for box, label, score in zip(boxes, labels, scores, strict=True):
        if not is_person_label(label):
            continue
        try:
            confidence = _finite(score, "confidence")
        except (TypeError, ValueError):
            continue
        if confidence < min_confidence or confidence > 1.0:
            continue
        if len(box) < 4:
            continue
        normalized = normalize_pixel_box(
            box[0], box[1], box[2], box[3], width=width, height=height
        )
        if normalized is None:
            continue
        observations.append(
            Observation(
                observation_id=uuid4(),
                source_id=frame.source_id,
                object_class=PERSON_CLASS,
                confidence=confidence,
                bounding_box=normalized,
                model_id=model_id,
                model_version=model_version,
                observed_at=stamped,
                camera_id=camera_id,
                track_id=None,
                media_timestamp=frame.captured_at,
                is_synthetic=frame.is_synthetic,
                mock_label=frame.mock_label,
            )
        )
    return observations
