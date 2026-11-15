from __future__ import annotations

from typing import Protocol, Self, runtime_checkable

from cv.frame import Frame


@runtime_checkable
class VideoSource(Protocol):
    """Pull-based frame source. Implementations must release native handles."""

    source_id: str

    def open(self) -> None: ...

    def read(self) -> Frame | None:
        """Return the next frame, or ``None`` at end of file."""

    def close(self) -> None: ...

    def __enter__(self) -> Self: ...

    def __exit__(self, *args: object) -> None: ...
