"""Lab response models for local-file person observations. Not incidents."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

_MOCK_SYNTHETIC_LABEL = "[MOCK / SYNTHETIC]"
_MAX_FRAMES = 30
_MAX_OBSERVATIONS = 200


class DemoBoundingBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @field_validator("x_min", "y_min", "x_max", "y_max")
    @classmethod
    def _unit_interval(cls, value: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("bounding box coordinates must be finite numbers")
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            raise ValueError("bounding box coordinates must be finite")
        if number < 0.0 or number > 1.0:
            raise ValueError("bounding box coordinates must be in [0, 1]")
        return number

    def model_post_init(self, _context: object) -> None:
        if self.x_max <= self.x_min or self.y_max <= self.y_min:
            raise ValueError("bounding box must have positive width and height")


class DemoObservation(BaseModel):
    observation_id: UUID
    object_class: Literal["person"]
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_box: DemoBoundingBox
    source_id: str = Field(min_length=1, max_length=200)
    model_id: str = Field(min_length=1, max_length=200)
    model_version: str = Field(min_length=1, max_length=80)
    observed_at: datetime
    media_timestamp: datetime | None = None
    frame_index: int = Field(ge=0)
    is_synthetic: Literal[True]
    mock_label: Literal["[MOCK / SYNTHETIC]"]
    @field_validator("confidence")
    @classmethod
    def _finite_confidence(cls, value: float) -> float:
        if isinstance(value, bool) or value != value or value in (float("inf"), float("-inf")):
            raise ValueError("confidence must be finite")
        return float(value)


class DemoRunRequest(BaseModel):
    max_frames: int = Field(default=_MAX_FRAMES, ge=1, le=_MAX_FRAMES)


class DemoObservationsResponse(BaseModel):
    """A lab snapshot. `record_kind` is never an incident."""

    record_kind: Literal["person_observation_demo"] = "person_observation_demo"
    demo_status: Literal["empty", "ready"]
    source_status: Literal["not_run", "local_mp4_demo"]
    source_id: str | None = None
    source_kind: Literal["file"] = "file"
    is_synthetic: Literal[True] = True
    mock_label: Literal["[MOCK / SYNTHETIC]"] = _MOCK_SYNTHETIC_LABEL
    frames_processed: int = Field(default=0, ge=0, le=_MAX_FRAMES)
    model_id: str | None = None
    model_version: str | None = None
    observations: list[DemoObservation] = Field(default_factory=list, max_length=_MAX_OBSERVATIONS)


def empty_demo_snapshot() -> DemoObservationsResponse:
    return DemoObservationsResponse(
        demo_status="empty",
        source_status="not_run",
        source_id=None,
        frames_processed=0,
        observations=[],
    )
