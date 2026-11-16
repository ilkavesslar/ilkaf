"""Public detection status. Observations are not incidents."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DetectionCapabilityOut(BaseModel):
    capability_id: str
    label: str
    status: Literal["available", "not_configured", "not_implemented", "error"]
    detail: str


class DetectionCapabilitiesResponse(BaseModel):
    capabilities: list[DetectionCapabilityOut]


class LiveObservationBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class LiveKeypoint(BaseModel):
    """COCO-17 joint. Missing joints use visibility 0 and null coordinates."""

    x: float | None = None
    y: float | None = None
    confidence: float = 0.0
    visibility: float = 0.0


class LiveObservationItem(BaseModel):
    observation_id: UUID
    camera_id: str
    object_class: str
    confidence: float
    bounding_box: LiveObservationBox
    observed_at: str
    track_id: int | None = None
    local_track_id: str | None = None
    global_person_id: str | None = None
    moving: bool = False
    waving: bool = False
    activity_class: str | None = None
    activity_confidence: float | None = None
    movement_state: str | None = None
    tracking_status: str | None = None
    keypoints: list[LiveKeypoint] = Field(default_factory=list)
    schema_version: str | None = None


class LiveObservationsResponse(BaseModel):
    """Cursor-ready observation feed. A missing sample stays not_connected."""

    status: Literal["not_connected", "ready", "error"] = "not_connected"
    detail: str = "Live AI detection is not currently connected."
    items: list[LiveObservationItem] = Field(default_factory=list)
    next_cursor: None = None
