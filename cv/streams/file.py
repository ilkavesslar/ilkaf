"""Prerecorded file ingest. Always ``[MOCK / SYNTHETIC]``. Not factory CCTV."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from cv.errors import VideoDecodeError, VideoSourceError
from cv.frame import MOCK_SYNTHETIC_LABEL, Frame
from cv.opencv import load_cv2


class FileSource:
    """Read frames from a local video file via optional OpenCV."""

    source_id: str

    def __init__(
        self,
        path: str | Path,
        *,
        source_id: str | None = None,
        timeline_origin: datetime | None = None,
    ) -> None:
        self._path = Path(path)
        self.source_id = source_id or self._path.name
        origin = timeline_origin if timeline_origin is not None else datetime.now(UTC)
        if origin.tzinfo is None:
            raise ValueError("timeline_origin must be timezone-aware (UTC)")
        self._timeline_origin = origin.astimezone(UTC)
        self._capture: Any | None = None
        self._index = -1

    def open(self) -> None:
        if self._capture is not None:
            return
        if not self._path.exists():
            raise VideoSourceError(f"video file does not exist: {self._path.name}")
        if not self._path.is_file():
            raise VideoSourceError(f"video path is not a file: {self._path.name}")
        cv2 = load_cv2()
        capture = cv2.VideoCapture(str(self._path))
        if not capture.isOpened():
            capture.release()
            raise VideoSourceError(f"unsupported or unreadable video file: {self._path.name}")
        self._capture = capture
        self._index = -1

    def read(self) -> Frame | None:
        if self._capture is None:
            raise VideoSourceError("source is not open")
        cv2 = load_cv2()
        capture = self._capture
        ok, image = capture.read()
        if not ok:
            return None
        if image is None:
            raise VideoDecodeError("decoder returned an empty frame")
        self._index += 1
        processed_at = datetime.now(UTC)
        position_ms = float(capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0)
        if position_ms < 0:
            position_ms = 0.0
        captured_at = self._timeline_origin + timedelta(milliseconds=position_ms)
        return Frame(
            data=image,
            index=self._index,
            captured_at=captured_at,
            processed_at=processed_at,
            source_id=self.source_id,
            is_synthetic=True,
            source_kind="file",
            mock_label=MOCK_SYNTHETIC_LABEL,
        )

    def close(self) -> None:
        capture = self._capture
        self._capture = None
        if capture is not None:
            capture.release()

    def __enter__(self) -> Self:
        self.open()
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        self.close()
