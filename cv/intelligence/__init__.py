"""ILKA Human Intelligence Engine. Probabilistic per-person observations, not incidents.

``HumanIntelligenceEngine`` is loaded lazily so ``cv.pose`` can import the
contract without a circular import.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from cv.intelligence.contract import (
    KEYPOINT_COUNT,
    SCHEMA_VERSION,
    ActivityClass,
    Keypoint,
    KeypointName,
    PersonIntelligenceObservation,
    missing_keypoints,
)
from cv.intelligence.tracker import CameraScopedTracker, TrackerConfig, TrackState

if TYPE_CHECKING:
    from cv.intelligence.engine import EngineConfig, HumanIntelligenceEngine

__all__ = [
    "KEYPOINT_COUNT",
    "SCHEMA_VERSION",
    "ActivityClass",
    "CameraScopedTracker",
    "EngineConfig",
    "HumanIntelligenceEngine",
    "Keypoint",
    "KeypointName",
    "PersonIntelligenceObservation",
    "TrackState",
    "TrackerConfig",
    "missing_keypoints",
]


def __getattr__(name: str) -> Any:
    if name in ("HumanIntelligenceEngine", "EngineConfig"):
        from cv.intelligence import engine

        return getattr(engine, name)
    raise AttributeError(f"module 'cv.intelligence' has no attribute {name!r}")
