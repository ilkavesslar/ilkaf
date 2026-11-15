"""Dev-only laptop webcam ingest. Frames stay ``[MOCK / SYNTHETIC]``.

Not a production camera, RTSP adapter, or incident source.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Any, Self

from cv.errors import VideoDecodeError, VideoSourceError
from cv.frame import MOCK_SYNTHETIC_LABEL, Frame
from cv.opencv import load_cv2


def _device_index(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("webcam index must be an integer")
    if value < 0:
        raise ValueError("webcam index must be at least 0")
    return value


def _copy_image(image: object) -> object:
    """Copy the decode buffer. OpenCV may reuse it on the next read."""

    copy = getattr(image, "copy", None)
    if not callable(copy):
        return image
    try:
        return copy()
    except Exception as exc:
        raise VideoDecodeError("webcam frame could not be copied") from exc


def _usable_image(image: object) -> bool:
    if image is None:
        return False
    shape = getattr(image, "shape", None)
    if not shape or len(shape) < 2:
        return False
    try:
        return int(shape[0]) > 0 and int(shape[1]) > 0
    except (TypeError, ValueError):
        return False


class WebcamSource:
    """Pull BGR frames from a local webcam. ``None`` is not used as end of stream."""

    source_id: str

    def __init__(self, index: int = 0, *, source_id: str | None = None) -> None:
        self._index = _device_index(index)
        self.source_id = source_id or f"webcam:{self._index}"
        self._capture: Any | None = None
        self._frame_index = -1

    def open(self) -> None:
        if self._capture is not None:
            return
        cv2 = load_cv2()
        try:
            capture = cv2.VideoCapture(self._index)
        except Exception as exc:
            raise VideoSourceError(f"webcam failed to open: {self.source_id}") from exc
        try:
            opened = bool(capture.isOpened())
        except Exception as exc:
            self._release_handle(capture)
            raise VideoSourceError(f"webcam failed to open: {self.source_id}") from exc
        if not opened:
            self._release_handle(capture)
            raise VideoSourceError(f"webcam failed to open: {self.source_id}")
        self._capture = capture
        self._frame_index = -1

    def read(self) -> Frame:
        if self._capture is None:
            raise VideoSourceError("source is not open")
        try:
            ok, image = self._capture.read()
        except Exception as exc:
            raise VideoSourceError(f"webcam read failed: {self.source_id}") from exc
        if not ok:
            raise VideoSourceError(f"webcam read failed: {self.source_id}")
        if not _usable_image(image):
            raise VideoDecodeError("decoder returned an empty frame")
        self._frame_index += 1
        moment = datetime.now(UTC)
        return Frame(
            data=_copy_image(image),
            index=self._frame_index,
            captured_at=moment,
            processed_at=moment,
            source_id=self.source_id,
            is_synthetic=True,
            source_kind="webcam",
            mock_label=MOCK_SYNTHETIC_LABEL,
        )

    def close(self) -> None:
        capture = self._capture
        self._capture = None
        if capture is not None:
            self._release_handle(capture)

    def _release_handle(self, capture: Any) -> None:
        try:
            capture.release()
        except Exception as exc:
            raise VideoSourceError(f"webcam failed to release: {self.source_id}") from exc

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
