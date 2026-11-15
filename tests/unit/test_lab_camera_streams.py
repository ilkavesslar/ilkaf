from __future__ import annotations

import time
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from app.services.lab_camera_streams import LabCameraError, LabCameraHub


class _Source:
    def __init__(self, camera: object) -> None:
        self.source_id = camera.source_id
        self.closed = 0
        self.index = -1

    def read(self) -> SimpleNamespace:
        self.index += 1
        time.sleep(0.01)
        return SimpleNamespace(
            data=f"{self.source_id}:{self.index}".encode(),
            source_id=self.source_id,
            is_synthetic=False,
            source_kind="rtsp",
            mock_label="",
            captured_at=datetime.now(UTC),
            index=self.index,
        )

    def close(self) -> None:
        self.closed += 1


def _hub() -> LabCameraHub:
    return LabCameraHub(opener=lambda camera: _Source(camera), encoder=lambda image: image)


def test_two_cameras_keep_separate_frames() -> None:
    hub = _hub()
    first = "vigi-c320i-192.168.1.17"
    second = "vigi-c320i-192.168.1.18"
    hub.acquire(first)
    hub.acquire(second)
    try:
        deadline = time.time() + 2
        while time.time() < deadline:
            seq_a, jpeg_a, _ = hub.latest_jpeg(first)
            seq_b, jpeg_b, _ = hub.latest_jpeg(second)
            if seq_a and seq_b and jpeg_a and jpeg_b:
                break
            time.sleep(0.02)
        assert jpeg_a is not None and jpeg_b is not None
        assert jpeg_a.startswith(b"vigi-c320i-192.168.1.17:")
        assert jpeg_b.startswith(b"vigi-c320i-192.168.1.18:")
        assert jpeg_a != jpeg_b
        assert hub.health(first).source_id == first
        assert hub.health(second).source_id == second
    finally:
        hub.release(first)
        hub.release(second)


def test_release_stops_the_reader_and_closes_the_source() -> None:
    opened: list[_Source] = []

    def opener(camera: object) -> _Source:
        source = _Source(camera)
        opened.append(source)
        return source

    hub = LabCameraHub(opener=opener, encoder=lambda image: image)
    camera_id = "vigi-c320i-192.168.1.17"
    hub.acquire(camera_id)
    hub.acquire(camera_id)
    hub.release(camera_id)
    assert hub.health(camera_id).state in {"connecting", "live"}
    hub.release(camera_id)
    assert hub.health(camera_id).state == "idle"
    assert opened
    assert opened[0].closed >= 1


def test_latest_frame_is_an_independent_copy() -> None:
    class Image:
        def __init__(self, mark: int) -> None:
            self.mark = mark

        def copy(self) -> Image:
            return Image(self.mark)

    class Source:
        def __init__(self, camera: object) -> None:
            self.source_id = camera.source_id
            self.closed = 0
            self.index = 0

        def read(self) -> SimpleNamespace:
            self.index += 1
            return SimpleNamespace(
                data=Image(self.index),
                source_id=self.source_id,
                is_synthetic=False,
                captured_at=datetime.now(UTC),
                index=self.index,
            )

        def close(self) -> None:
            self.closed += 1

    hub = LabCameraHub(opener=lambda camera: Source(camera), encoder=lambda image: b"jpeg")
    camera_id = "vigi-c320i-192.168.1.17"
    hub.acquire(camera_id)
    try:
        frame = None
        deadline = time.time() + 2
        while time.time() < deadline and frame is None:
            frame = hub.latest_frame(camera_id)
            time.sleep(0.02)
        assert frame is not None
        frame.data.mark = -1
        again = hub.latest_frame(camera_id)
        assert again is not None
        assert again.data is not frame.data
        assert again.data.mark != -1
    finally:
        hub.release(camera_id)


def test_unknown_camera_is_rejected() -> None:
    hub = _hub()
    with pytest.raises(LabCameraError, match="unknown_camera"):
        hub.camera("other-camera")


def test_multipart_chunk_contains_only_that_camera() -> None:
    hub = _hub()
    camera_id = "vigi-c320i-192.168.1.17"
    chunks = hub.multipart(camera_id)
    try:
        chunk = next(chunks)
    finally:
        chunks.close()
    assert b"Content-Type: image/jpeg" in chunk
    assert b"Content-Length:" in chunk
    assert camera_id.encode() in chunk
    assert b"192.168.1.18" not in chunk
    assert hub.health(camera_id).state == "idle"


def test_missing_credentials_do_not_include_a_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ILKA_CAMERA_PASSWORD", raising=False)
    from app.services.lab_camera_streams import LabCamera, camera_rtsp_url

    camera = LabCamera("vigi-c320i-192.168.1.17", "Camera 01", "192.168.1.17", 554, "/stream1")
    with pytest.raises(LabCameraError, match="credentials_missing"):
        camera_rtsp_url(camera)
