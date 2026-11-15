"""Decide when a copied frame is due for inference. Does not open a camera."""

from __future__ import annotations

from cv.detectors.base import PersonDetector
from cv.frame import Frame
from cv.observation import Observation


class InferenceClock:
    """Camera frame rate and inference rate stay separate."""

    def __init__(self, interval_s: float) -> None:
        if isinstance(interval_s, bool) or not isinstance(interval_s, (int, float)):
            raise TypeError("interval_s must be a number of seconds")
        if interval_s <= 0:
            raise ValueError("interval_s must be greater than 0")
        self.interval_s = float(interval_s)
        self._last: dict[str, float] = {}

    def due(self, camera_id: str, now: float) -> bool:
        previous = self._last.get(camera_id)
        if previous is not None and now - previous < self.interval_s:
            return False
        self._last[camera_id] = now
        return True


def sample_person(
    detector: PersonDetector,
    frame: Frame,
    camera_id: str,
    clock: InferenceClock,
    now: float,
) -> list[Observation] | None:
    """Run the detector when the interval has elapsed.

    ``None`` means this frame was skipped. An empty list means inference ran
    and found nothing. This does not create an incident.
    """

    if not clock.due(camera_id, now):
        return None
    return detector.detect(frame)
