from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

MOCK_SYNTHETIC_LABEL = "[MOCK / SYNTHETIC]"


def normalize_mock_label(*, is_synthetic: bool, mock_label: str) -> str:
    """Keep ``is_synthetic`` and ``mock_label`` from contradicting each other.

    Synthetic records always use ``MOCK_SYNTHETIC_LABEL``. Non-synthetic records
    never keep that label: the default is cleared to ``""``, and any other
    caller-supplied tag is left unchanged.
    """

    if is_synthetic:
        return MOCK_SYNTHETIC_LABEL
    if mock_label == MOCK_SYNTHETIC_LABEL:
        return ""
    return mock_label


@dataclass(frozen=True, slots=True)
class Frame:
    """One decoded video frame.

    ``data`` is typically a BGR ndarray when OpenCV is used. Tests without
    OpenCV may pass any object (for example ``bytes``).

    ``captured_at`` is the source timeline in UTC. File ingest maps position
    onto an origin. RTSP ingest uses the read clock. ``processed_at`` is when
    ILKA finished decoding the frame.

    File frames stay synthetic (``source_kind="file"``). RTSP frames use
    ``source_kind="rtsp"``, ``is_synthetic=False``, and an empty
    ``mock_label``. Webcam frames are dev-only and stay synthetic
    (``source_kind="webcam"``). ``is_synthetic`` and ``mock_label`` are
    normalized together: see ``normalize_mock_label``.
    """

    data: Any
    index: int
    captured_at: datetime
    processed_at: datetime
    source_id: str
    is_synthetic: bool = True
    source_kind: Literal["file", "rtsp", "webcam"] = "file"
    mock_label: str = MOCK_SYNTHETIC_LABEL

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "mock_label",
            normalize_mock_label(is_synthetic=self.is_synthetic, mock_label=self.mock_label),
        )
