from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cv.errors import CvDependencyError, VideoDecodeError, VideoSourceError
from cv.frame import MOCK_SYNTHETIC_LABEL
from cv.streams.base import VideoSource
from cv.streams.rtsp import RtspSource

_URL = "rtsp://operator:s3cret-pass@camera.example:554/live"
_SAFE_ID = "rtsp:camera.example:554/live"
_WHEN = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)


class _Image:
    def __init__(self, size: int = 6) -> None:
        self.size = size
        self.shape = (2, 2, 3)


class _Capture:
    def __init__(self, reads: list[tuple[bool, object | None]], *, opened: bool = True) -> None:
        self._reads = list(reads)
        self._opened = opened
        self.released = False

    def isOpened(self) -> bool:
        return self._opened

    def read(self) -> tuple[bool, object | None]:
        if not self._reads:
            return False, None
        return self._reads.pop(0)

    def release(self) -> None:
        self.released = True


class _Cv2:
    CAP_PROP_OPEN_TIMEOUT_MSEC = 53
    CAP_PROP_READ_TIMEOUT_MSEC = 54
    CAP_FFMPEG = 1900

    def __init__(self, scripted: list[_Capture]) -> None:
        self._scripted = list(scripted)
        self.calls: list[tuple[object, object, object]] = []

    def VideoCapture(self, url: object, api: object, params: object) -> _Capture:
        self.calls.append((url, api, params))
        if not self._scripted:
            raise AssertionError("unexpected VideoCapture call")
        return self._scripted.pop(0)


def _source(
    cv2: _Cv2,
    monkeypatch: pytest.MonkeyPatch,
    *,
    url: str = _URL,
    source_id: str | None = None,
    max_reconnect_attempts: int = 2,
    retry_delay_s: float = 0.25,
    delays: list[float] | None = None,
) -> RtspSource:
    monkeypatch.setattr("cv.streams.rtsp.load_cv2", lambda: cv2)
    recorded = delays if delays is not None else []

    def _sleep(seconds: float) -> None:
        recorded.append(seconds)

    return RtspSource(
        url,
        source_id=source_id,
        open_timeout_ms=1500,
        read_timeout_ms=2500,
        max_reconnect_attempts=max_reconnect_attempts,
        retry_delay_s=retry_delay_s,
        clock=lambda: _WHEN,
        sleeper=_sleep,
    )


def _assert_secret_free(text: str) -> None:
    assert "s3cret-pass" not in text
    assert "operator" not in text
    assert _URL not in text
    assert "@" not in text


def test_rtsp_source_matches_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    source = _source(_Cv2([]), monkeypatch, url="rtsp://camera.example/live")
    assert isinstance(source, VideoSource)
    assert source.source_id == "rtsp:camera.example/live"


def test_rejects_urls_that_are_not_rtsp(monkeypatch: pytest.MonkeyPatch) -> None:
    cv2 = _Cv2([])
    monkeypatch.setattr("cv.streams.rtsp.load_cv2", lambda: cv2)
    for url in ("", "http://camera.example/live", "camera.example/live", "rtsp:///live"):
        with pytest.raises(VideoSourceError):
            RtspSource(url)
    spaced = "rtsp://camera.example/live stream"
    with pytest.raises(VideoSourceError, match="unsupported characters"):
        RtspSource(spaced)
    assert cv2.calls == []


def test_default_source_id_omits_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    source = _source(_Cv2([]), monkeypatch)
    assert source.source_id == _SAFE_ID
    _assert_secret_free(source.source_id)


def test_explicit_source_id_cannot_carry_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cv.streams.rtsp.load_cv2", lambda: _Cv2([]))
    with pytest.raises(VideoSourceError, match="must not contain credentials") as raised:
        RtspSource(_URL, source_id="cam-s3cret-pass")
    _assert_secret_free(str(raised.value))


def test_username_that_matches_a_host_label_keeps_the_public_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("cv.streams.rtsp.load_cv2", lambda: _Cv2([]))
    source = RtspSource("rtsp://cam:s3cret-pass@cam.example/live", sleeper=lambda _seconds: None)
    assert source.source_id == "rtsp:cam.example/live"
    assert "s3cret-pass" not in source.source_id
    with pytest.raises(VideoSourceError, match="must not contain credentials") as raised:
        RtspSource(
            "rtsp://cam:s3cret-pass@cam.example/live",
            source_id="lab-cam",
            sleeper=lambda _seconds: None,
        )
    _assert_secret_free(str(raised.value))


def test_rtsps_and_ipv6_ids_omit_userinfo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cv.streams.rtsp.load_cv2", lambda: _Cv2([]))
    secure = RtspSource("rtsps://camera.example/live", sleeper=lambda _seconds: None)
    assert secure.source_id == "rtsps:camera.example/live"
    ipv6 = RtspSource("rtsp://[2001:db8::1]:554/live", sleeper=lambda _seconds: None)
    assert ipv6.source_id == "rtsp:[2001:db8::1]:554/live"


def test_open_failure_releases_handle_and_hides_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed = _Capture([], opened=False)
    cv2 = _Cv2([failed])
    source = _source(cv2, monkeypatch, max_reconnect_attempts=0, retry_delay_s=0)
    with pytest.raises(VideoSourceError, match="failed to open") as raised:
        source.open()
    text = str(raised.value)
    _assert_secret_free(text)
    assert _SAFE_ID in text
    assert failed.released is True
    assert cv2.calls[0][1] == 1900
    assert cv2.calls[0][2] == [53, 1500, 54, 2500]
    assert source.source_id == _SAFE_ID


def test_missing_timeout_support_does_not_open(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Bare:
        def VideoCapture(self, *_args: object) -> _Capture:
            raise AssertionError("capture must not be constructed")

    monkeypatch.setattr("cv.streams.rtsp.load_cv2", lambda: _Bare())
    source = RtspSource("rtsp://camera.example/live", sleeper=lambda _seconds: None)
    with pytest.raises(VideoSourceError, match="cannot enforce RTSP timeouts"):
        source.open()


def test_timeout_constructor_mismatch_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Old:
        CAP_PROP_OPEN_TIMEOUT_MSEC = 53
        CAP_PROP_READ_TIMEOUT_MSEC = 54
        CAP_FFMPEG = 1900

        def VideoCapture(self, *_args: object) -> _Capture:
            raise TypeError("params are not supported")

    monkeypatch.setattr("cv.streams.rtsp.load_cv2", lambda: _Old())
    source = RtspSource(
        "rtsp://camera.example/live",
        max_reconnect_attempts=0,
        sleeper=lambda _seconds: None,
    )
    with pytest.raises(VideoSourceError, match="cannot enforce RTSP timeouts") as raised:
        source.open()
    assert isinstance(raised.value.__cause__, TypeError)


def test_successful_read_is_a_real_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    image = _Image()
    cv2 = _Cv2([_Capture([(True, image)])])
    source = _source(cv2, monkeypatch, max_reconnect_attempts=0, retry_delay_s=0)
    with source as opened:
        frame = opened.read()
    assert frame is not None
    assert frame.data is image
    assert frame.index == 0
    assert frame.source_id == _SAFE_ID
    assert frame.source_kind == "rtsp"
    assert frame.is_synthetic is False
    assert frame.mock_label == ""
    assert frame.mock_label != MOCK_SYNTHETIC_LABEL
    assert frame.captured_at == _WHEN
    assert frame.processed_at == _WHEN
    assert cv2.calls[0][0] == _URL


def test_empty_reads_reconnect_then_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    delays: list[float] = []
    first = _Capture([(True, None)])
    second = _Capture([(True, _Image(0))])
    cv2 = _Cv2([first, second])
    source = _source(
        cv2,
        monkeypatch,
        max_reconnect_attempts=1,
        retry_delay_s=0.25,
        delays=delays,
    )
    source.open()
    with pytest.raises(VideoDecodeError, match="empty frame") as raised:
        source.read()
    _assert_secret_free(str(raised.value))
    assert len(cv2.calls) == 2
    assert delays == [0.25]
    assert first.released is True
    assert second.released is True
    source.close()
    source.close()


def test_consecutive_reads_reuse_one_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    first = _Image()
    second = _Image()
    capture = _Capture([(True, first), (True, second)])
    delays: list[float] = []
    cv2 = _Cv2([capture])
    source = _source(
        cv2,
        monkeypatch,
        max_reconnect_attempts=2,
        retry_delay_s=0.25,
        delays=delays,
    )
    source.open()
    frame_a = source.read()
    frame_b = source.read()
    assert frame_a is not None and frame_b is not None
    assert frame_a.data is first
    assert frame_b.data is second
    assert (frame_a.index, frame_b.index) == (0, 1)
    assert frame_a.source_kind == frame_b.source_kind == "rtsp"
    assert frame_a.is_synthetic is frame_b.is_synthetic is False
    assert len(cv2.calls) == 1
    assert cv2.calls[0][2] == [53, 1500, 54, 2500]
    assert delays == []
    assert capture.released is False
    source.close()
    assert capture.released is True
    source.close()


def test_numpy_frames_are_copied_before_return(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Buffer:
        def __init__(self) -> None:
            self.size = 6
            self.shape = (2, 2, 3)

        def copy(self) -> _Buffer:
            twin = _Buffer()
            twin.size = self.size
            return twin

    _Buffer.__module__ = "numpy"
    image = _Buffer()
    source = _source(
        _Cv2([_Capture([(True, image)])]),
        monkeypatch,
        max_reconnect_attempts=0,
        retry_delay_s=0,
    )
    with source as opened:
        frame = opened.read()
    assert frame is not None
    assert frame.data is not image
    assert frame.data.shape == image.shape
    assert frame.data.size == image.size


def test_reconnect_can_return_the_next_real_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    image = _Image()
    cv2 = _Cv2([_Capture([(False, None)]), _Capture([(True, image)])])
    source = _source(cv2, monkeypatch, max_reconnect_attempts=1, retry_delay_s=0)
    source.open()
    frame = source.read()
    assert frame is not None
    assert frame.data is image
    assert frame.index == 0
    assert frame.is_synthetic is False
    assert frame.source_kind == "rtsp"
    assert frame.mock_label == ""
    assert len(cv2.calls) == 2
    assert cv2.calls[0][2] == cv2.calls[1][2] == [53, 1500, 54, 2500]


def test_open_retries_stop_at_the_configured_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    delays: list[float] = []
    first = _Capture([], opened=False)
    second = _Capture([], opened=False)
    cv2 = _Cv2([first, second, _Capture([])])
    source = _source(
        cv2,
        monkeypatch,
        max_reconnect_attempts=1,
        retry_delay_s=0.25,
        delays=delays,
    )
    with pytest.raises(VideoSourceError, match="failed to open") as raised:
        source.open()
    _assert_secret_free(str(raised.value))
    assert len(cv2.calls) == 2
    assert delays == [0.25]
    assert first.released is True
    assert second.released is True


def test_failed_reads_stop_at_the_reconnect_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    delays: list[float] = []
    captures = [_Capture([(False, None)]) for _ in range(3)]
    cv2 = _Cv2(captures)
    source = _source(
        cv2,
        monkeypatch,
        max_reconnect_attempts=2,
        retry_delay_s=0.5,
        delays=delays,
    )
    source.open()
    with pytest.raises(VideoSourceError, match="2 reconnect attempts") as raised:
        source.read()
    _assert_secret_free(str(raised.value))
    assert len(cv2.calls) == 3
    assert delays == [0.5, 0.5]
    assert all(item.released for item in captures)
    with pytest.raises(VideoSourceError, match="not open"):
        source.read()


def test_read_before_open_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    source = _source(_Cv2([]), monkeypatch, url="rtsp://camera.example/live")
    with pytest.raises(VideoSourceError, match="not open"):
        source.read()


def test_close_before_open_and_second_open_are_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    cv2 = _Cv2([_Capture([(True, _Image())])])
    source = _source(cv2, monkeypatch, url="rtsp://camera.example/live", retry_delay_s=0)
    source.close()
    source.open()
    source.open()
    assert len(cv2.calls) == 1
    source.close()
    source.close()


def test_open_succeeds_on_a_later_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    delays: list[float] = []
    image = _Image()
    failed = _Capture([], opened=False)
    opened = _Capture([(True, image)])
    cv2 = _Cv2([failed, opened])
    source = _source(
        cv2,
        monkeypatch,
        max_reconnect_attempts=1,
        retry_delay_s=0.25,
        delays=delays,
    )
    source.open()
    frame = source.read()
    assert frame is not None
    assert frame.data is image
    assert frame.index == 0
    assert delays == [0.25]
    assert len(cv2.calls) == 2
    assert failed.released is True
    source.close()
    assert opened.released is True
    source.close()
    assert opened.released is True


def test_zero_retry_delay_does_not_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    delays: list[float] = []
    captures = [_Capture([(False, None)]), _Capture([(False, None)])]
    cv2 = _Cv2(captures)
    source = _source(
        cv2,
        monkeypatch,
        max_reconnect_attempts=1,
        retry_delay_s=0,
        delays=delays,
    )
    source.open()
    with pytest.raises(VideoSourceError, match="1 reconnect attempts"):
        source.read()
    assert delays == []
    assert all(item.released for item in captures)


def test_missing_opencv_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    delays: list[float] = []

    def _missing() -> object:
        raise CvDependencyError("OpenCV is required for video ingest")

    monkeypatch.setattr("cv.streams.rtsp.load_cv2", _missing)
    source = RtspSource(
        "rtsp://camera.example/live",
        max_reconnect_attempts=3,
        retry_delay_s=0.5,
        sleeper=delays.append,
    )
    with pytest.raises(CvDependencyError, match="OpenCV is required"):
        source.open()
    assert delays == []


def test_open_failure_keeps_a_safe_backend_cause(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Loud(_Cv2):
        def VideoCapture(self, url: object, api: object, params: object) -> _Capture:
            self.calls.append((url, api, params))
            raise RuntimeError("network unreachable")

    delays: list[float] = []
    source = _source(
        _Loud([]),
        monkeypatch,
        max_reconnect_attempts=1,
        retry_delay_s=0.25,
        delays=delays,
    )
    with pytest.raises(VideoSourceError, match="failed to open") as raised:
        source.open()
    assert delays == [0.25]
    cause = raised.value.__cause__
    assert isinstance(cause, RuntimeError)
    assert str(cause) == "network unreachable"


def test_backend_open_exception_hides_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Loud(_Cv2):
        def VideoCapture(self, url: object, api: object, params: object) -> _Capture:
            raise RuntimeError(f"ffmpeg open failed for {url}")

    source = _source(_Loud([]), monkeypatch, max_reconnect_attempts=0, retry_delay_s=0)
    with pytest.raises(VideoSourceError, match="failed to open") as raised:
        source.open()
    _assert_secret_free(str(raised.value))
    assert raised.value.__cause__ is None


def test_is_opened_exception_releases_and_hides_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Unstable(_Capture):
        def isOpened(self) -> bool:
            raise RuntimeError(f"probe failed for {_URL}")

    capture = _Unstable([])
    source = _source(
        _Cv2([capture]),
        monkeypatch,
        max_reconnect_attempts=0,
        retry_delay_s=0,
    )
    with pytest.raises(VideoSourceError, match="failed to open") as raised:
        source.open()
    _assert_secret_free(str(raised.value))
    assert raised.value.__cause__ is None
    assert capture.released is True


def test_read_exception_reconnects_without_leaking_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Loud(_Capture):
        def read(self) -> tuple[bool, object | None]:
            raise RuntimeError("decoder timed out")

    first = _Loud([(True, _Image())])
    second = _Capture([(False, None)])
    delays: list[float] = []
    source = _source(
        _Cv2([first, second]),
        monkeypatch,
        max_reconnect_attempts=1,
        retry_delay_s=0.25,
        delays=delays,
    )
    source.open()
    with pytest.raises(VideoSourceError, match="1 reconnect attempts") as raised:
        source.read()
    assert delays == [0.25]
    assert first.released is True
    assert second.released is True
    assert isinstance(raised.value.__cause__, RuntimeError)
    assert "decoder timed out" in str(raised.value.__cause__)
    _assert_secret_free(str(raised.value))
    _assert_secret_free(str(raised.value.__cause__))


def test_read_exception_with_credentials_drops_the_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Loud(_Capture):
        def read(self) -> tuple[bool, object | None]:
            raise RuntimeError(f"decoder failed for {_URL}")

    source = _source(
        _Cv2([_Loud([])]),
        monkeypatch,
        max_reconnect_attempts=0,
        retry_delay_s=0,
    )
    source.open()
    with pytest.raises(VideoSourceError, match="0 reconnect attempts") as raised:
        source.read()
    _assert_secret_free(str(raised.value))
    assert raised.value.__cause__ is None


def test_frame_shape_matches_the_detector_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    image = _Image()
    source = _source(
        _Cv2([_Capture([(True, image)])]),
        monkeypatch,
        max_reconnect_attempts=0,
        retry_delay_s=0,
    )
    with source as opened:
        frame = opened.read()
    assert frame is not None
    shape = frame.data.shape
    assert len(shape) >= 3
    assert int(shape[0]) > 0
    assert int(shape[1]) > 0
    assert int(shape[2]) >= 3
    assert frame.source_kind == "rtsp"
    assert frame.is_synthetic is False
    assert frame.mock_label == ""


def test_blank_source_id_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cv.streams.rtsp.load_cv2", lambda: _Cv2([]))
    with pytest.raises(VideoSourceError, match="source_id is missing"):
        RtspSource("rtsp://camera.example/live", source_id="   ")


def test_reconnect_open_failure_keeps_a_safe_cause(monkeypatch: pytest.MonkeyPatch) -> None:
    class _ThenClosed(_Cv2):
        def VideoCapture(self, url: object, api: object, params: object) -> _Capture:
            self.calls.append((url, api, params))
            if len(self.calls) == 1:
                return _Capture([(False, None)])
            raise RuntimeError("reconnect refused")

    source = _source(
        _ThenClosed([]),
        monkeypatch,
        max_reconnect_attempts=1,
        retry_delay_s=0,
    )
    source.open()
    with pytest.raises(VideoSourceError, match="1 reconnect attempts") as raised:
        source.read()
    cause = raised.value.__cause__
    assert isinstance(cause, RuntimeError)
    assert str(cause) == "reconnect refused"


def test_naive_clock_does_not_emit_a_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    capture = _Capture([(True, _Image())])
    monkeypatch.setattr("cv.streams.rtsp.load_cv2", lambda: _Cv2([capture]))
    source = RtspSource(
        "rtsp://camera.example/live",
        max_reconnect_attempts=0,
        retry_delay_s=0,
        clock=lambda: datetime(2026, 10, 16, 12, 0),  # noqa: DTZ001 — naive clock must be rejected
        sleeper=lambda _seconds: None,
    )
    source.open()
    with pytest.raises(ValueError, match="timezone-aware"):
        source.read()
    assert capture.released is False
    source.close()
    assert capture.released is True


def test_rejects_unbounded_retry_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cv.streams.rtsp.load_cv2", lambda: _Cv2([]))
    with pytest.raises(ValueError, match="open_timeout_ms"):
        RtspSource("rtsp://camera.example/live", open_timeout_ms=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="max_reconnect_attempts"):
        RtspSource("rtsp://camera.example/live", max_reconnect_attempts=99)
    with pytest.raises(ValueError, match="retry_delay_s"):
        RtspSource("rtsp://camera.example/live", retry_delay_s=float("inf"))
    with pytest.raises(ValueError, match="open_timeout_ms"):
        RtspSource("rtsp://camera.example/live", open_timeout_ms=0)
    with pytest.raises(ValueError, match="read_timeout_ms"):
        RtspSource("rtsp://camera.example/live", read_timeout_ms=-1)
    with pytest.raises(ValueError, match="max_reconnect_attempts"):
        RtspSource("rtsp://camera.example/live", max_reconnect_attempts=-1)
    with pytest.raises(ValueError, match="retry_delay_s"):
        RtspSource("rtsp://camera.example/live", retry_delay_s=-0.1)
    with pytest.raises(VideoSourceError, match="must be a string"):
        RtspSource(None)  # type: ignore[arg-type]
