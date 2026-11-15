from __future__ import annotations

from types import SimpleNamespace

import pytest

from cv.errors import CvDependencyError, VideoDecodeError, VideoSourceError
from cv.frame import MOCK_SYNTHETIC_LABEL
from cv.streams.base import VideoSource
from cv.streams.webcam import WebcamSource


class _Image:
    def __init__(self, token: int) -> None:
        self.token = token
        self.shape = (4, 6, 3)
        self.copied = False

    def copy(self) -> _Image:
        cloned = _Image(self.token)
        cloned.copied = True
        return cloned


class _Capture:
    def __init__(
        self,
        reads: list[tuple[bool, object | None]],
        *,
        opened: bool = True,
    ) -> None:
        self._reads = list(reads)
        self._opened = opened
        self.released = 0

    def isOpened(self) -> bool:
        return self._opened

    def read(self) -> tuple[bool, object | None]:
        if not self._reads:
            return False, None
        return self._reads.pop(0)

    def release(self) -> None:
        self.released += 1


class _Cv2:
    def __init__(self, capture: _Capture) -> None:
        self.capture = capture
        self.calls: list[int] = []

    def VideoCapture(self, index: int) -> _Capture:
        self.calls.append(index)
        return self.capture


def _install(monkeypatch: pytest.MonkeyPatch, cv2: _Cv2) -> None:
    monkeypatch.setattr("cv.streams.webcam.load_cv2", lambda: cv2)


def test_webcam_source_matches_protocol() -> None:
    source = WebcamSource(0, source_id="cam")
    assert isinstance(source, VideoSource)
    assert source.source_id == "cam"


def test_default_source_id_uses_the_index() -> None:
    source = WebcamSource(2)
    assert source.source_id == "webcam:2"


def test_invalid_index_is_rejected() -> None:
    with pytest.raises(TypeError, match="integer"):
        WebcamSource(True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="at least 0"):
        WebcamSource(-1)


def test_read_before_open_raises() -> None:
    source = WebcamSource(0)
    with pytest.raises(VideoSourceError, match="not open"):
        source.read()


def test_missing_opencv_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom() -> object:
        raise CvDependencyError("opencv missing")

    monkeypatch.setattr("cv.streams.webcam.load_cv2", _boom)
    source = WebcamSource(0)
    with pytest.raises(CvDependencyError, match="opencv missing"):
        source.open()


def test_failed_open_releases_the_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    capture = _Capture([], opened=False)
    cv2 = _Cv2(capture)
    _install(monkeypatch, cv2)
    source = WebcamSource(0)
    with pytest.raises(VideoSourceError, match="failed to open"):
        source.open()
    assert cv2.calls == [0]
    assert capture.released == 1
    assert source._capture is None


def test_open_uses_the_device_index_only(monkeypatch: pytest.MonkeyPatch) -> None:
    capture = _Capture([ (True, _Image(1)) ])
    cv2 = _Cv2(capture)
    _install(monkeypatch, cv2)
    source = WebcamSource(3, source_id="desk")
    source.open()
    try:
        assert cv2.calls == [3]
        assert capture.released == 0
    finally:
        source.close()


def test_read_returns_a_copied_synthetic_webcam_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    original = _Image(7)
    capture = _Capture([(True, original)])
    _install(monkeypatch, _Cv2(capture))
    with WebcamSource(0, source_id="desk") as source:
        frame = source.read()
    assert frame.source_kind == "webcam"
    assert frame.is_synthetic is True
    assert frame.mock_label == MOCK_SYNTHETIC_LABEL
    assert frame.source_id == "desk"
    assert frame.index == 0
    assert frame.captured_at.tzinfo is not None
    assert frame.processed_at.tzinfo is not None
    assert frame.data is not original
    assert frame.data.token == 7
    assert frame.data.copied is True
    assert frame.data.shape == (4, 6, 3)


def test_numpy_frame_is_an_independent_copy(monkeypatch: pytest.MonkeyPatch) -> None:
    np = pytest.importorskip("numpy")
    image = np.zeros((2, 3, 3), dtype=np.uint8)
    image[0, 0] = (1, 2, 3)
    capture = _Capture([(True, image)])
    _install(monkeypatch, _Cv2(capture))
    source = WebcamSource(1, source_id="numpy")
    source.open()
    try:
        frame = source.read()
        image[0, 0] = (9, 9, 9)
    finally:
        source.close()
    assert frame.data[0, 0].tolist() == [1, 2, 3]
    assert frame.source_kind == "webcam"


def test_failed_read_is_not_end_of_file(monkeypatch: pytest.MonkeyPatch) -> None:
    capture = _Capture([(False, None)])
    _install(monkeypatch, _Cv2(capture))
    source = WebcamSource(0)
    source.open()
    try:
        with pytest.raises(VideoSourceError, match="read failed"):
            source.read()
    finally:
        source.close()


def test_empty_frame_raises_decode_error(monkeypatch: pytest.MonkeyPatch) -> None:
    capture = _Capture([(True, SimpleNamespace(shape=(0, 0, 3)))])
    _install(monkeypatch, _Cv2(capture))
    source = WebcamSource(0)
    source.open()
    try:
        with pytest.raises(VideoDecodeError, match="empty frame"):
            source.read()
    finally:
        source.close()


def test_close_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    capture = _Capture([(True, _Image(1))])
    _install(monkeypatch, _Cv2(capture))
    source = WebcamSource(0)
    source.open()
    source.close()
    source.close()
    assert capture.released == 1
    with pytest.raises(VideoSourceError, match="not open"):
        source.read()
