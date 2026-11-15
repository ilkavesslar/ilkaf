from __future__ import annotations

from typing import Protocol, runtime_checkable

from cv.frame import Frame
from cv.observation import Observation


@runtime_checkable
class PersonDetector(Protocol):
    """Frame-level person detector. Outputs observations, not incidents."""

    model_id: str
    model_version: str

    def detect(self, frame: Frame) -> list[Observation]:
        """Return zero or more person observations for ``frame``."""
