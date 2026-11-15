"""Latest sampled observations for one camera. Not an incident store."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC
from typing import Literal

from cv.observation import Observation

from app.schemas.detection import LiveObservationBox, LiveObservationItem

_MAX_ITEMS = 50


def to_live_observation(
    item: Observation,
    camera_id: str,
    *,
    track_id: int | None = None,
    moving: bool = False,
    waving: bool = False,
) -> LiveObservationItem:
    """Public detection fields only. No model path, stream URL, or credentials."""

    box = item.bounding_box
    return LiveObservationItem(
        observation_id=item.observation_id,
        camera_id=camera_id,
        object_class=item.object_class,
        confidence=item.confidence,
        bounding_box=LiveObservationBox(
            x_min=box.x_min,
            y_min=box.y_min,
            x_max=box.x_max,
            y_max=box.y_max,
        ),
        observed_at=item.observed_at.astimezone(UTC).isoformat(),
        track_id=track_id,
        moving=moving,
        waving=waving,
    )


@dataclass(frozen=True, slots=True)
class CameraSample:
    status: Literal["ready", "error"]
    detail: str
    items: list[LiveObservationItem]


class DetectionState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_camera: dict[str, CameraSample] = {}

    def publish(self, camera_id: str, items: list[LiveObservationItem]) -> None:
        bounded = list(items[:_MAX_ITEMS])
        detail = "No active observations." if not bounded else "Latest sampled person observations."
        with self._lock:
            self._by_camera[camera_id] = CameraSample("ready", detail, bounded)

    def publish_error(self, camera_id: str, detail: str) -> None:
        with self._lock:
            self._by_camera[camera_id] = CameraSample("error", detail, [])

    def forget(self, camera_id: str) -> None:
        with self._lock:
            self._by_camera.pop(camera_id, None)

    def read(self, camera_id: str) -> CameraSample | None:
        """``None`` means inference has not published for this camera."""

        with self._lock:
            return self._by_camera.get(camera_id)

    def clear(self) -> None:
        with self._lock:
            self._by_camera.clear()


_state = DetectionState()


def get_detection_state() -> DetectionState:
    return _state


def record_person_sample(
    detector: object,
    frame: object,
    camera_id: str,
    clock: object,
    now: float,
) -> bool:
    """Publish one sampled result. The caller supplies an already copied frame.

    This does not open RTSP and does not run inside an HTTP handler.
    """

    from cv.sampling import sample_person

    found = sample_person(detector, frame, camera_id, clock, now)
    if found is None:
        return False
    get_detection_state().publish(
        camera_id,
        [to_live_observation(item, camera_id) for item in found],
    )
    return True
