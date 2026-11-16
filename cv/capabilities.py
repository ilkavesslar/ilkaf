"""Public detection capability status. No paths, credentials, or live inference."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from cv.detectors.person_cpu import WEIGHTS_ENV, verify_weights_file
from cv.errors import DetectorModelError

CapabilityStatus = Literal["available", "not_configured", "not_implemented", "error"]

_DEFAULT_WEIGHTS = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "models"
    / "ssdlite320_mobilenet_v3_large_coco.pth"
)


@dataclass(frozen=True, slots=True)
class DetectionCapability:
    capability_id: str
    label: str
    status: CapabilityStatus
    detail: str


def _weights_candidate() -> Path | None:
    raw = os.environ.get(WEIGHTS_ENV, "").strip()
    if raw:
        return Path(raw)
    if _DEFAULT_WEIGHTS.is_file():
        return _DEFAULT_WEIGHTS
    return None


def probe_person() -> DetectionCapability:
    """Report whether the existing CPU person detector can be loaded. Does not run it."""

    try:
        import torch  # noqa: F401
        from torchvision.models import detection as _detection  # noqa: F401
    except ImportError:
        return DetectionCapability(
            "person",
            "Person detection",
            "not_configured",
            "The CPU person detector runtime is not installed.",
        )
    path = _weights_candidate()
    if path is None or not path.is_file():
        return DetectionCapability(
            "person",
            "Person detection",
            "not_configured",
            "Person detector weights are not configured.",
        )
    try:
        verify_weights_file(path)
    except DetectorModelError:
        return DetectionCapability(
            "person",
            "Person detection",
            "error",
            "Person detector weights failed the integrity check.",
        )
    return DetectionCapability(
        "person",
        "Person detection",
        "available",
        "The CPU person detector is installed. Live camera inference is not connected.",
    )


def _unimplemented() -> list[DetectionCapability]:
    return [
        DetectionCapability(
            "tracking",
            "Multi-person tracking",
            "available",
            "Camera-scoped anonymous tracking is available (PROVISIONAL).",
        ),
        DetectionCapability(
            "pose",
            "COCO-17 pose estimation",
            "not_configured",
            "Pose requires a local MediaPipe .task model under data/models/.",
        ),
        DetectionCapability(
            "activity",
            "Temporal activity recognition",
            "available",
            "Rule-based temporal activities are available (PROVISIONAL; uncalibrated).",
        ),
        DetectionCapability(
            "anonymous_identity",
            "Anonymous cross-camera identity",
            "available",
            "Probabilistic anonymous IDs only; no facial recognition.",
        ),
        DetectionCapability(
            "ppe",
            "PPE detection",
            "not_implemented",
            "No PPE model is implemented.",
        ),
        DetectionCapability(
            "fire_smoke",
            "Fire and smoke detection",
            "not_implemented",
            "No fire or smoke model is implemented.",
        ),
    ]


def _unchecked_person() -> DetectionCapability:
    return DetectionCapability(
        "person",
        "Person detection",
        "not_configured",
        "Person detector readiness has not been checked.",
    )


_cache_lock = threading.Lock()
_cached: list[DetectionCapability] | None = None


def clear_capability_cache() -> None:
    """Test helper. Does not import Torch."""

    global _cached
    with _cache_lock:
        _cached = None


def detection_capabilities() -> list[DetectionCapability]:
    """Return the last readiness snapshot. Does not import Torch or hash weights."""

    with _cache_lock:
        if _cached is None:
            return [_unchecked_person(), *_unimplemented()]
        return list(_cached)


def refresh_capabilities() -> list[DetectionCapability]:
    """Run the expensive person-detector check once, off the request path."""

    snapshot = [probe_person(), *_unimplemented()]
    global _cached
    with _cache_lock:
        _cached = snapshot
    return list(snapshot)


def schedule_capability_probe() -> None:
    """Start one daemon probe. Safe to call from application startup."""

    threading.Thread(
        target=refresh_capabilities,
        name="ilka-detection-capability",
        daemon=True,
    ).start()
