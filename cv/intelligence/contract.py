"""Typed person-intelligence contract. Probabilistic observations, not incidents.

Every value here is either measured by a CV stage or explicitly marked as
unavailable (``None`` / ``visibility=0`` / ``ActivityClass.UNKNOWN``). Nothing
is filled in to make a record look complete.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum, StrEnum
from math import isfinite
from typing import Any, Literal, cast
from uuid import UUID

from cv.frame import normalize_mock_label
from cv.observation import BoundingBox

SCHEMA_VERSION = "1.0.0"
KEYPOINT_COUNT = 17

TrackingStatus = Literal["active", "lost", "tentative"]
MovementState = Literal["unknown", "stationary", "moving"]
TRACKING_STATUSES: tuple[str, ...] = ("active", "lost", "tentative")
MOVEMENT_STATES: tuple[str, ...] = ("unknown", "stationary", "moving")


class ActivityClass(StrEnum):
    STANDING = "standing"
    WALKING = "walking"
    RUNNING = "running"
    SITTING = "sitting"
    BENDING = "bending"
    WAVING = "waving"
    FALLING = "falling"
    PERSON_DOWN = "person_down"
    UNKNOWN = "unknown"


class KeypointName(IntEnum):
    """COCO-17 keypoint order."""

    NOSE = 0
    LEFT_EYE = 1
    RIGHT_EYE = 2
    LEFT_EAR = 3
    RIGHT_EAR = 4
    LEFT_SHOULDER = 5
    RIGHT_SHOULDER = 6
    LEFT_ELBOW = 7
    RIGHT_ELBOW = 8
    LEFT_WRIST = 9
    RIGHT_WRIST = 10
    LEFT_HIP = 11
    RIGHT_HIP = 12
    LEFT_KNEE = 13
    RIGHT_KNEE = 14
    LEFT_ANKLE = 15
    RIGHT_ANKLE = 16


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    number = float(value)
    if not isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def _unit(value: object, name: str) -> float:
    number = _finite(value, name)
    if number < 0.0 or number > 1.0:
        raise ValueError(f"{name} must be in [0.0, 1.0]")
    return number


def _aware_utc(value: object, name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware (UTC)")
    return value.astimezone(UTC)


def _non_empty(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{name} is required")
    return stripped


def _optional_str(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _non_empty(value, name)


@dataclass(frozen=True, slots=True)
class Keypoint:
    """One joint in normalized image coordinates.

    ``visibility`` is the estimator's probability that the joint is visible.
    ``visibility == 0`` means not observed: ``x``/``y`` may then be ``None``
    and must never be invented. Observed joints must carry coordinates.
    """

    x: float | None
    y: float | None
    confidence: float
    visibility: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", _unit(self.confidence, "keypoint confidence"))
        object.__setattr__(self, "visibility", _unit(self.visibility, "keypoint visibility"))
        if (self.x is None) != (self.y is None):
            raise ValueError("keypoint x and y must both be set or both be None")
        if self.x is None:
            if self.visibility > 0.0:
                raise ValueError("a visible keypoint must have coordinates")
            return
        object.__setattr__(self, "x", _unit(self.x, "keypoint x"))
        object.__setattr__(self, "y", _unit(self.y, "keypoint y"))

    @classmethod
    def missing(cls) -> Keypoint:
        return cls(x=None, y=None, confidence=0.0, visibility=0.0)

    @property
    def observed(self) -> bool:
        return self.x is not None and self.visibility > 0.0

    def to_dict(self) -> dict[str, float | None]:
        return {
            "x": self.x,
            "y": self.y,
            "confidence": self.confidence,
            "visibility": self.visibility,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Keypoint:
        _require_keys(data, ("x", "y", "confidence", "visibility"), "keypoint")
        return cls(
            x=data["x"],
            y=data["y"],
            confidence=data["confidence"],
            visibility=data["visibility"],
        )


def missing_keypoints() -> tuple[Keypoint, ...]:
    """Seventeen unobserved joints. Used when no pose model ran or matched."""

    return tuple(Keypoint.missing() for _ in range(KEYPOINT_COUNT))


def _require_keys(data: Mapping[str, Any], keys: Sequence[str], name: str) -> None:
    if not isinstance(data, Mapping):
        raise TypeError(f"{name} must be a mapping")
    absent = [key for key in keys if key not in data]
    if absent:
        raise ValueError(f"{name} is missing required fields: {', '.join(absent)}")


def _parse_datetime(value: object, name: str) -> datetime:
    if isinstance(value, datetime):
        return _aware_utc(value, name)
    if not isinstance(value, str):
        raise TypeError(f"{name} must be an ISO 8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO 8601 string") from exc
    return _aware_utc(parsed, name)


@dataclass(frozen=True, slots=True)
class PersonIntelligenceObservation:
    """Per-frame, per-track human intelligence. Not an incident, alert, or identity.

    ``local_track_id`` is scoped to one camera session. ``global_person_id`` is
    an anonymous cross-camera hypothesis (never a face or named identity) and
    is ``None`` until a matcher assigned one.
    """

    observation_id: UUID
    camera_id: str
    source_id: str
    timestamp: datetime
    local_track_id: str
    bbox: BoundingBox
    detection_confidence: float
    keypoints: tuple[Keypoint, ...]
    activity_class: ActivityClass
    activity_confidence: float
    movement_state: MovementState
    tracking_status: TrackingStatus
    model_versions: dict[str, str]
    activity_started_at: datetime | None = None
    activity_duration_s: float | None = None
    global_person_id: str | None = None
    frame_id: str | None = None
    is_synthetic: bool = True
    mock_label: str = ""
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"unsupported schema_version: {self.schema_version!r}")
        if not isinstance(self.observation_id, UUID):
            raise TypeError("observation_id must be a UUID")
        object.__setattr__(self, "camera_id", _non_empty(self.camera_id, "camera_id"))
        object.__setattr__(self, "source_id", _non_empty(self.source_id, "source_id"))
        object.__setattr__(self, "timestamp", _aware_utc(self.timestamp, "timestamp"))
        object.__setattr__(
            self, "local_track_id", _non_empty(self.local_track_id, "local_track_id")
        )
        object.__setattr__(
            self, "global_person_id", _optional_str(self.global_person_id, "global_person_id")
        )
        object.__setattr__(self, "frame_id", _optional_str(self.frame_id, "frame_id"))
        if not isinstance(self.bbox, BoundingBox):
            raise TypeError("bbox must be a BoundingBox")
        object.__setattr__(
            self,
            "detection_confidence",
            _unit(self.detection_confidence, "detection_confidence"),
        )
        keypoints = tuple(self.keypoints)
        if len(keypoints) != KEYPOINT_COUNT:
            raise ValueError(f"keypoints must contain exactly {KEYPOINT_COUNT} COCO-17 joints")
        if not all(isinstance(point, Keypoint) for point in keypoints):
            raise TypeError("keypoints must be Keypoint instances")
        object.__setattr__(self, "keypoints", keypoints)
        object.__setattr__(self, "activity_class", ActivityClass(self.activity_class))
        object.__setattr__(
            self,
            "activity_confidence",
            _unit(self.activity_confidence, "activity_confidence"),
        )
        if self.activity_class is ActivityClass.UNKNOWN and self.activity_confidence > 0.0:
            raise ValueError("unknown activity must have activity_confidence 0.0")
        self._validate_activity_timing()
        if self.movement_state not in MOVEMENT_STATES:
            raise ValueError(f"movement_state must be one of {MOVEMENT_STATES}")
        if self.tracking_status not in TRACKING_STATUSES:
            raise ValueError(f"tracking_status must be one of {TRACKING_STATUSES}")
        if not isinstance(self.model_versions, Mapping):
            raise TypeError("model_versions must be a mapping")
        versions: dict[str, str] = {}
        for key, value in self.model_versions.items():
            versions[_non_empty(key, "model_versions key")] = _non_empty(
                value, f"model_versions[{key!r}]"
            )
        object.__setattr__(self, "model_versions", versions)
        if not isinstance(self.is_synthetic, bool):
            raise TypeError("is_synthetic must be a bool")
        object.__setattr__(
            self,
            "mock_label",
            normalize_mock_label(is_synthetic=self.is_synthetic, mock_label=self.mock_label),
        )

    def _validate_activity_timing(self) -> None:
        started = self.activity_started_at
        duration = self.activity_duration_s
        if (started is None) != (duration is None):
            raise ValueError("activity_started_at and activity_duration_s must be set together")
        if started is None or duration is None:
            return
        started = _aware_utc(started, "activity_started_at")
        object.__setattr__(self, "activity_started_at", started)
        seconds = _finite(duration, "activity_duration_s")
        if seconds < 0.0:
            raise ValueError("activity_duration_s must be >= 0")
        if started > self.timestamp:
            raise ValueError("activity_started_at must not be after timestamp")
        object.__setattr__(self, "activity_duration_s", seconds)

    def to_dict(self) -> dict[str, Any]:
        started = self.activity_started_at
        return {
            "schema_version": self.schema_version,
            "observation_id": str(self.observation_id),
            "camera_id": self.camera_id,
            "source_id": self.source_id,
            "frame_id": self.frame_id,
            "timestamp": self.timestamp.isoformat(),
            "local_track_id": self.local_track_id,
            "global_person_id": self.global_person_id,
            "bbox": {
                "x_min": self.bbox.x_min,
                "y_min": self.bbox.y_min,
                "x_max": self.bbox.x_max,
                "y_max": self.bbox.y_max,
            },
            "detection_confidence": self.detection_confidence,
            "keypoints": [point.to_dict() for point in self.keypoints],
            "activity_class": self.activity_class.value,
            "activity_confidence": self.activity_confidence,
            "activity_started_at": started.isoformat() if started is not None else None,
            "activity_duration_s": self.activity_duration_s,
            "movement_state": self.movement_state,
            "tracking_status": self.tracking_status,
            "model_versions": dict(self.model_versions),
            "is_synthetic": self.is_synthetic,
            "mock_label": self.mock_label,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PersonIntelligenceObservation:
        """Strictly parse a serialized record. Missing fields are errors, not defaults."""

        _require_keys(
            data,
            (
                "schema_version",
                "observation_id",
                "camera_id",
                "source_id",
                "frame_id",
                "timestamp",
                "local_track_id",
                "global_person_id",
                "bbox",
                "detection_confidence",
                "keypoints",
                "activity_class",
                "activity_confidence",
                "activity_started_at",
                "activity_duration_s",
                "movement_state",
                "tracking_status",
                "model_versions",
                "is_synthetic",
                "mock_label",
            ),
            "person intelligence observation",
        )
        bbox = data["bbox"]
        _require_keys(bbox, ("x_min", "y_min", "x_max", "y_max"), "bbox")
        raw_keypoints = data["keypoints"]
        if not isinstance(raw_keypoints, Sequence) or isinstance(raw_keypoints, (str, bytes)):
            raise TypeError("keypoints must be a list")
        raw_id = data["observation_id"]
        if not isinstance(raw_id, str):
            raise TypeError("observation_id must be a UUID string")
        started = data["activity_started_at"]
        return cls(
            schema_version=data["schema_version"],
            observation_id=UUID(raw_id),
            camera_id=data["camera_id"],
            source_id=data["source_id"],
            frame_id=data["frame_id"],
            timestamp=_parse_datetime(data["timestamp"], "timestamp"),
            local_track_id=data["local_track_id"],
            global_person_id=data["global_person_id"],
            bbox=BoundingBox(
                x_min=bbox["x_min"],
                y_min=bbox["y_min"],
                x_max=bbox["x_max"],
                y_max=bbox["y_max"],
            ),
            detection_confidence=data["detection_confidence"],
            keypoints=tuple(Keypoint.from_dict(point) for point in raw_keypoints),
            activity_class=ActivityClass(data["activity_class"]),
            activity_confidence=data["activity_confidence"],
            activity_started_at=(
                _parse_datetime(started, "activity_started_at") if started is not None else None
            ),
            activity_duration_s=data["activity_duration_s"],
            movement_state=cast(MovementState, data["movement_state"]),
            tracking_status=cast(TrackingStatus, data["tracking_status"]),
            model_versions=data["model_versions"],
            is_synthetic=data["is_synthetic"],
            mock_label=data["mock_label"],
        )
