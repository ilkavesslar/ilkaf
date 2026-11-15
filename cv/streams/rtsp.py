"""Provisional RTSP ingest. Not ONVIF, detection, or production camera integration.

The URL is kept only for the OpenCV open call. Errors and ``source_id`` omit
userinfo. A backend that cannot apply connection and read timeouts is rejected.

A dead stream raises after a bounded reconnect. It does not return ``None`` and
it does not substitute a synthetic frame. ``None`` remains the file-source end
of stream. Missing OpenCV and a backend that cannot enforce timeouts fail on
the first attempt.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from math import isfinite
from types import TracebackType
from typing import Any, NoReturn, Self
from urllib.parse import SplitResult, unquote, urlsplit

from cv.errors import CvDependencyError, VideoDecodeError, VideoSourceError
from cv.frame import Frame
from cv.opencv import load_cv2

_MAX_URL_LENGTH = 2048
_MAX_SOURCE_ID_LENGTH = 200
_MAX_TIMEOUT_MS = 120_000
_MAX_RECONNECT_ATTEMPTS = 5
_MAX_RETRY_DELAY_S = 30.0
_SCHEMES = frozenset({"rtsp", "rtsps"})


def _positive_millis(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer millisecond timeout")
    if value < 1 or value > _MAX_TIMEOUT_MS:
        raise ValueError(f"{name} must be from 1 to {_MAX_TIMEOUT_MS}")
    return value


def _reconnect_attempts(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("max_reconnect_attempts must be an integer")
    if value < 0 or value > _MAX_RECONNECT_ATTEMPTS:
        raise ValueError(
            f"max_reconnect_attempts must be from 0 to {_MAX_RECONNECT_ATTEMPTS}"
        )
    return value


def _retry_delay(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("retry_delay_s must be a finite number of seconds")
    delay = float(value)
    if not isfinite(delay) or delay < 0 or delay > _MAX_RETRY_DELAY_S:
        raise ValueError(f"retry_delay_s must be from 0 to {_MAX_RETRY_DELAY_S}")
    return delay


def _parse_rtsp_url(url: object) -> tuple[str, SplitResult]:
    if not isinstance(url, str):
        raise VideoSourceError("rtsp URL must be a string")
    raw = url.strip()
    if not raw or len(raw) > _MAX_URL_LENGTH:
        raise VideoSourceError("rtsp URL is missing or too long")
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in raw):
        raise VideoSourceError("rtsp URL contains unsupported characters")
    parts = urlsplit(raw)
    if parts.scheme.lower() not in _SCHEMES:
        raise VideoSourceError("rtsp URL must use the rtsp or rtsps scheme")
    if not parts.hostname:
        raise VideoSourceError("rtsp URL must include a host")
    return raw, parts


def _credential_fragments(url: str, parts: SplitResult) -> tuple[str, ...]:
    found: list[str] = [url]
    for value in (parts.username, parts.password):
        if value:
            found.append(value)
    if "@" in parts.netloc:
        userinfo = parts.netloc.rsplit("@", 1)[0]
        if userinfo:
            found.append(userinfo)
            decoded = unquote(userinfo)
            if decoded != userinfo:
                found.append(decoded)
            user, separator, password = userinfo.partition(":")
            if separator:
                decoded_parts = (user, password, unquote(user), unquote(password))
                found.extend(item for item in decoded_parts if item)
    return tuple(dict.fromkeys(found))


def _contains_fragment(text: str, fragments: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(fragment.lower() in lowered for fragment in fragments if fragment)


def _source_id_exposes_secret(ident: str, public_id: str, secrets: tuple[str, ...]) -> bool:
    """Reject secrets that are not already part of the credential-free locator.

    A username that is also a host label appears in the default id. Removing
    that public locator first keeps the host usable and still rejects a
    source id that adds a password or userinfo.
    """

    remainder = ident.lower().replace(public_id.lower(), "")
    return _contains_fragment(remainder, secrets)


def _default_source_id(parts: SplitResult) -> str:
    host = parts.hostname or ""
    if ":" in host:
        host = f"[{host}]"
    port = f":{parts.port}" if parts.port else ""
    path = parts.path or ""
    return f"{parts.scheme.lower()}:{host}{port}{path}"


def _detach_image(image: object) -> object:
    """Copy NumPy frames. OpenCV may reuse the decode buffer on the next read."""

    module = getattr(type(image), "__module__", "")
    if module != "numpy" and not module.startswith("numpy."):
        return image
    copy = getattr(image, "copy", None)
    if not callable(copy):
        return image
    return copy()


def _usable_image(image: object) -> bool:
    if image is None:
        return False
    size = getattr(image, "size", None)
    if isinstance(size, int) and not isinstance(size, bool):
        return size > 0
    shape = getattr(image, "shape", None)
    if not shape:
        return False
    try:
        return all(int(dim) > 0 for dim in shape)
    except (TypeError, ValueError):
        return False


class RtspSource:
    """Pull RTSP frames through OpenCV. Failures stay on this camera.

    ``max_reconnect_attempts`` counts extra attempts after the first failure.
    ``open`` tries that many reconnects. ``read`` uses the open capture once,
    then reconnects up to the same bound. A positive ``retry_delay_s`` is
    applied before each reconnect and is not applied before the first try.
    """

    source_id: str

    def __init__(
        self,
        url: str,
        *,
        source_id: str | None = None,
        open_timeout_ms: int = 5_000,
        read_timeout_ms: int = 5_000,
        max_reconnect_attempts: int = 2,
        retry_delay_s: float = 0.5,
        clock: Callable[[], datetime] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        raw, parts = _parse_rtsp_url(url)
        self._url = raw
        self._secrets = _credential_fragments(raw, parts)
        self.source_id = self._validated_source_id(source_id, parts)
        self._open_timeout_ms = _positive_millis(open_timeout_ms, "open_timeout_ms")
        self._read_timeout_ms = _positive_millis(read_timeout_ms, "read_timeout_ms")
        self._max_reconnect_attempts = _reconnect_attempts(max_reconnect_attempts)
        self._retry_delay_s = _retry_delay(retry_delay_s)
        self._clock = clock if clock is not None else lambda: datetime.now(UTC)
        self._sleeper = sleeper if sleeper is not None else _default_sleep
        self._capture: Any | None = None
        self._index = -1
        self._backend_error: BaseException | None = None

    def _validated_source_id(self, source_id: str | None, parts: SplitResult) -> str:
        public_id = _default_source_id(parts)
        ident = public_id if source_id is None else source_id.strip()
        if not ident or len(ident) > _MAX_SOURCE_ID_LENGTH:
            raise VideoSourceError("source_id is missing or too long")
        if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in ident):
            raise VideoSourceError("source_id contains unsupported characters")
        if (
            "@" in ident
            or "://" in ident
            or _source_id_exposes_secret(ident, public_id, self._secrets)
        ):
            raise VideoSourceError("source_id must not contain credentials or a URL")
        return ident

    def _raise(self, message: str, exc: BaseException | None = None) -> NoReturn:
        if exc is None or _contains_fragment(f"{exc}", self._secrets):
            raise VideoSourceError(message) from None
        raise VideoSourceError(message) from exc

    def _pause_before_retry(self) -> None:
        if self._retry_delay_s > 0:
            self._sleeper(self._retry_delay_s)

    def _note_backend_error(self, exc: BaseException) -> None:
        if _contains_fragment(f"{exc}", self._secrets):
            self._backend_error = None
            return
        self._backend_error = exc

    def _release_handle(self, capture: Any) -> None:
        try:
            capture.release()
        except Exception as exc:
            self._raise(f"rtsp source failed to release: {self.source_id}", exc)

    def _release(self) -> None:
        capture = self._capture
        self._capture = None
        if capture is None:
            return
        self._release_handle(capture)

    def _open_capture(self) -> None:
        cv2 = load_cv2()
        open_prop = getattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC", None)
        read_prop = getattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC", None)
        api = getattr(cv2, "CAP_FFMPEG", None)
        if open_prop is None or read_prop is None or api is None:
            self._raise(f"OpenCV cannot enforce RTSP timeouts for {self.source_id}")
        params = [int(open_prop), self._open_timeout_ms, int(read_prop), self._read_timeout_ms]
        try:
            capture = cv2.VideoCapture(self._url, api, params)
        except TypeError as exc:
            self._raise(f"OpenCV cannot enforce RTSP timeouts for {self.source_id}", exc)
        except Exception as exc:
            self._raise(f"rtsp source failed to open: {self.source_id}", exc)
        try:
            opened = bool(capture.isOpened())
        except Exception as exc:
            self._release_handle(capture)
            self._raise(f"rtsp source failed to open: {self.source_id}", exc)
        if not opened:
            self._release_handle(capture)
            self._raise(f"rtsp source failed to open: {self.source_id}")
        self._capture = capture

    def open(self) -> None:
        if self._capture is not None:
            return
        tries = self._max_reconnect_attempts + 1
        last = "rtsp source failed to open: " + self.source_id
        last_cause: BaseException | None = None
        for attempt in range(tries):
            if attempt:
                self._release()
                self._pause_before_retry()
            try:
                self._open_capture()
            except CvDependencyError:
                self._release()
                raise
            except VideoSourceError as exc:
                self._release()
                if "cannot enforce RTSP timeouts" in str(exc):
                    raise
                last = str(exc)
                last_cause = exc.__cause__
                continue
            return
        self._raise(last, last_cause)

    def _read_image(self) -> tuple[str, object | None]:
        capture = self._capture
        if capture is None:
            return "closed", None
        try:
            ok, image = capture.read()
        except Exception as exc:
            self._note_backend_error(exc)
            return "failed", None
        if not ok:
            return "failed", None
        if not _usable_image(image):
            return "empty", None
        return "ok", image

    def _make_frame(self, image: object) -> Frame:
        moment = self._clock()
        if moment.tzinfo is None:
            raise ValueError("clock must return timezone-aware UTC")
        moment = moment.astimezone(UTC)
        self._index += 1
        return Frame(
            data=_detach_image(image),
            index=self._index,
            captured_at=moment,
            processed_at=moment,
            source_id=self.source_id,
            is_synthetic=False,
            source_kind="rtsp",
            mock_label="",
        )

    def read(self) -> Frame | None:
        if self._capture is None:
            raise VideoSourceError("source is not open")
        self._backend_error = None
        kind, image = self._read_image()
        if kind == "ok":
            return self._make_frame(image)
        for _attempt in range(self._max_reconnect_attempts):
            self._release()
            self._pause_before_retry()
            try:
                self._open_capture()
            except CvDependencyError:
                self._release()
                raise
            except VideoSourceError as exc:
                if "cannot enforce RTSP timeouts" in str(exc):
                    raise
                cause = exc.__cause__
                if cause is not None and not _contains_fragment(f"{cause}", self._secrets):
                    self._backend_error = cause
                kind = "failed"
                continue
            kind, image = self._read_image()
            if kind == "ok":
                return self._make_frame(image)
        self._release()
        if kind == "empty":
            raise VideoDecodeError(f"rtsp source returned an empty frame: {self.source_id}")
        self._raise(
            f"rtsp read failed for {self.source_id} "
            f"after {self._max_reconnect_attempts} reconnect attempts",
            self._backend_error,
        )

    def close(self) -> None:
        self._release()

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


def _default_sleep(seconds: float) -> None:
    import time

    time.sleep(seconds)
