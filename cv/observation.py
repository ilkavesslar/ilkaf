"""Typed probabilistic observation contract. Not an incident, alert, or event."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import isfinite
from uuid import UUID

from cv.frame import MOCK_SYNTHETIC_LABEL, normalize_mock_label


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    number = float(value)
    if not isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def _aware_utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware (UTC)")
    return value.astimezone(UTC)


def _non_empty(value: str, name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{name} is required")
    return stripped


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Axis-aligned box in normalized image coordinates ``[0.0, 1.0]``."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def __post_init__(self) -> None:
        for name in ("x_min", "y_min", "x_max", "y_max"):
            number = _finite_number(getattr(self, name), name)
            if number < 0.0 or number > 1.0:
                raise ValueError(f"{name} must be in [0.0, 1.0]")
        if self.x_max <= self.x_min:
            raise ValueError("x_max must be greater than x_min")
        if self.y_max <= self.y_min:
            raise ValueError("y_max must be greater than y_min")


@dataclass(frozen=True, slots=True)
class Observation:
    """Probabilistic detector output.

    This type is **not** an incident, alert, event, or safety conclusion
    (ADR 0003). Downstream stages remain unimplemented.

    ``media_timestamp`` is the source/media timeline when known (same meaning
    as ``Frame.captured_at``). ``observed_at`` is the UTC wall clock when this
    observation was produced (same meaning as ``Frame.processed_at``).

    ``is_synthetic`` and ``mock_label`` follow ``normalize_mock_label``.
    """

    observation_id: UUID
    source_id: str
    object_class: str
    confidence: float
    bounding_box: BoundingBox
    model_id: str
    model_version: str
    observed_at: datetime
    camera_id: str | None = None
    track_id: str | None = None
    media_timestamp: datetime | None = None
    is_synthetic: bool = True
    mock_label: str = MOCK_SYNTHETIC_LABEL

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, UUID):
            raise TypeError("observation_id must be a UUID")
        object.__setattr__(self, "source_id", _non_empty(self.source_id, "source_id"))
        object.__setattr__(self, "object_class", _non_empty(self.object_class, "object_class"))
        object.__setattr__(self, "model_id", _non_empty(self.model_id, "model_id"))
        object.__setattr__(self, "model_version", _non_empty(self.model_version, "model_version"))
        confidence = _finite_number(self.confidence, "confidence")
        if confidence < 0.0 or confidence > 1.0:
            raise ValueError("confidence must be in [0.0, 1.0]")
        if not isinstance(self.bounding_box, BoundingBox):
            raise TypeError("bounding_box must be a BoundingBox")
        object.__setattr__(self, "observed_at", _aware_utc(self.observed_at, "observed_at"))
        if self.camera_id is not None:
            object.__setattr__(self, "camera_id", _non_empty(self.camera_id, "camera_id"))
        if self.track_id is not None:
            object.__setattr__(self, "track_id", _non_empty(self.track_id, "track_id"))
        if self.media_timestamp is not None:
            object.__setattr__(
                self,
                "media_timestamp",
                _aware_utc(self.media_timestamp, "media_timestamp"),
            )
        object.__setattr__(
            self,
            "mock_label",
            normalize_mock_label(is_synthetic=self.is_synthetic, mock_label=self.mock_label),
        )
