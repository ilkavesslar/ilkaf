from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from cv.errors import CvDependencyError, VideoDecodeError, VideoSourceError
from cv.frame import MOCK_SYNTHETIC_LABEL
from cv.streams.base import VideoSource
from cv.streams.file import FileSource


def _write_color_clip(path: Path, frame_count: int = 6) -> None:
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    width, height = 32, 24
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        10.0,
        (width, height),
    )
    if not writer.isOpened():
        pytest.skip("OpenCV VideoWriter could not create a test clip on this host")
    try:
        for index in range(frame_count):
            image = np.zeros((height, width, 3), dtype=np.uint8)
            image[:, :] = (index * 20, 40, 80)
            writer.write(image)
    finally:
        writer.release()


def test_file_source_matches_protocol() -> None:
    source = FileSource("unused.avi", source_id="proto")
    assert isinstance(source, VideoSource)


def test_default_source_id_is_filename() -> None:
    source = FileSource("folder/people-detection (1).mp4")
    assert source.source_id == "people-detection (1).mp4"


def test_missing_file_raises(tmp_path: Path) -> None:
    source = FileSource(tmp_path / "missing.avi", source_id="missing")
    with pytest.raises(VideoSourceError, match="does not exist"):
        source.open()


def test_directory_is_not_a_file(tmp_path: Path) -> None:
    source = FileSource(tmp_path, source_id="dir")
    with pytest.raises(VideoSourceError, match="not a file"):
        source.open()


def test_read_before_open_raises() -> None:
    source = FileSource("unused.avi", source_id="unopened")
    with pytest.raises(VideoSourceError, match="not open"):
        source.read()


def test_file_source_requires_opencv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    stub = tmp_path / "stub.avi"
    stub.write_bytes(b"stub")

    def _boom() -> object:
        raise CvDependencyError("opencv missing")

    monkeypatch.setattr("cv.streams.file.load_cv2", _boom)
    source = FileSource(stub, source_id="need-cv")
    with pytest.raises(CvDependencyError, match="opencv missing"):
        source.open()


def test_unsupported_file_is_safe(tmp_path: Path) -> None:
    pytest.importorskip("cv2")
    junk = tmp_path / "not-a-video.txt"
    junk.write_text("not a video", encoding="utf-8")
    source = FileSource(junk, source_id="junk")
    try:
        source.open()
    except VideoSourceError:
        return
    try:
        assert source.read() is None
    finally:
        source.close()


def test_naive_timeline_origin_rejected() -> None:
    naive = datetime(2026, 9, 20, 12, 0)  # noqa: DTZ001
    with pytest.raises(ValueError, match="timeline_origin"):
        FileSource("unused.avi", timeline_origin=naive)


def test_timezone_aware_timeline_origin_is_stored_as_utc() -> None:
    offset = timezone(timedelta(hours=5, minutes=30))
    origin = datetime(2026, 9, 20, 17, 30, tzinfo=offset)
    source = FileSource("unused.avi", source_id="tz", timeline_origin=origin)
    assert source._timeline_origin == datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    assert source._timeline_origin.tzinfo == UTC


def test_empty_decoded_frame_raises_video_decode_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cv.streams.file.load_cv2", lambda: SimpleNamespace(CAP_PROP_POS_MSEC=0))
    source = FileSource("unused.avi", source_id="empty-decode")
    source._capture = SimpleNamespace(read=lambda: (True, None))
    with pytest.raises(VideoDecodeError, match="empty frame"):
        source.read()


def test_reads_synthetic_frames_until_eof(tmp_path: Path) -> None:
    clip = tmp_path / "synthetic.avi"
    _write_color_clip(clip, frame_count=6)
    origin = datetime(2026, 9, 20, tzinfo=UTC)
    frames = []
    with FileSource(clip, source_id="lab-file", timeline_origin=origin) as source:
        assert source.source_id == "lab-file"
        while True:
            frame = source.read()
            if frame is None:
                break
            frames.append(frame)
        assert source.read() is None
    assert len(frames) == 6
    assert [frame.index for frame in frames] == list(range(6))
    first = frames[0]
    assert first.is_synthetic is True
    assert first.mock_label == MOCK_SYNTHETIC_LABEL
    assert first.source_kind == "file"
    assert first.source_id == "lab-file"
    assert first.captured_at.tzinfo is not None
    assert first.processed_at.tzinfo is not None
    assert first.captured_at >= origin
    assert first.data.shape[0] == 24
    assert first.data.shape[1] == 32


def test_close_is_idempotent(tmp_path: Path) -> None:
    clip = tmp_path / "once.avi"
    _write_color_clip(clip, frame_count=2)
    source = FileSource(clip, source_id="once")
    source.open()
    source.close()
    source.close()
