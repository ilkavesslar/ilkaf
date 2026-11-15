"""One shared RTSP reader per lab camera. The browser never sees the RTSP URL.

Each camera keeps a single latest JPEG. Older frames are discarded. The reader
stops when the last client leaves. Production requests are refused by the API.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote

from app.core.config import get_settings

_CAMERA_1 = "vigi-c320i-192.168.1.17"
_CAMERA_2 = "vigi-c320i-192.168.1.18"


@dataclass(frozen=True, slots=True)
class LabCamera:
    camera_id: str
    name: str
    host: str
    port: int
    path: str

    @property
    def source_id(self) -> str:
        return self.camera_id


def copy_image(image: object) -> object:
    """Return an independent image buffer. The caller owns the result."""

    if isinstance(image, (bytes, bytearray)):
        return bytes(image)
    clone = getattr(image, "copy", None)
    if callable(clone):
        return clone()
    raise LabCameraError("frame_not_copyable")


@dataclass(frozen=True, slots=True)
class SharedFrame:
    """One copied raw frame from the camera reader. Not a second RTSP session."""

    camera_id: str
    sequence: int
    captured_at: datetime
    width: int | None
    height: int | None
    data: object


@dataclass(slots=True)
class LabCameraHealth:
    camera_id: str
    name: str
    host: str
    source_id: str
    state: str
    last_frame_at: datetime | None = None
    frame_width: int | None = None
    frame_height: int | None = None
    error: str | None = None


def lab_camera_definitions() -> tuple[LabCamera, LabCamera]:
    def _host(name: str, default: str) -> str:
        return os.environ.get(name, default).strip() or default

    def _port(name: str) -> int:
        raw = os.environ.get(name, "554").strip() or "554"
        return int(raw)

    def _path(name: str) -> str:
        raw = os.environ.get(name, "/stream1").strip() or "/stream1"
        return raw if raw.startswith("/") else f"/{raw}"

    return (
        LabCamera(
            _CAMERA_1,
            "Camera 01",
            _host("ILKA_LAB_CAMERA_1_HOST", "192.168.1.13"),
            _port("ILKA_LAB_CAMERA_1_PORT"),
            _path("ILKA_LAB_CAMERA_1_PATH"),
        ),
        LabCamera(
            _CAMERA_2,
            "Camera 02",
            _host("ILKA_LAB_CAMERA_2_HOST", "192.168.1.15"),
            _port("ILKA_LAB_CAMERA_2_PORT"),
            _path("ILKA_LAB_CAMERA_2_PATH"),
        ),
    )


def camera_rtsp_url(camera: LabCamera) -> str:
    user = os.environ.get("ILKA_CAMERA_USERNAME", "")
    password = os.environ.get("ILKA_CAMERA_PASSWORD", "")
    if not user or not password:
        raise LabCameraError("credentials_missing")
    return (
        f"rtsp://{quote(user, safe='')}:{quote(password, safe='')}"
        f"@{camera.host}:{camera.port}{camera.path}"
    )


class LabCameraError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _encode_jpeg(image: object) -> bytes:
    if isinstance(image, (bytes, bytearray)):
        return bytes(image)
    import cv2

    ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    if not ok:
        raise LabCameraError("encode_failed")
    return encoded.tobytes()


def _open_rtsp(camera: LabCamera) -> object:
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    from cv.streams.rtsp import RtspSource

    source = RtspSource(
        camera_rtsp_url(camera),
        source_id=camera.source_id,
        open_timeout_ms=8_000,
        read_timeout_ms=8_000,
        max_reconnect_attempts=1,
        retry_delay_s=0.5,
    )
    source.open()
    return source


class LabCameraHub:
    """Refcounted readers. Tests inject ``opener`` and ``encoder``."""

    def __init__(
        self,
        opener: object | None = None,
        encoder: object | None = None,
        on_start: object | None = None,
        on_stop: object | None = None,
    ) -> None:
        self._opener = opener or _open_rtsp
        self._encoder = encoder or _encode_jpeg
        self._on_start = on_start
        self._on_stop = on_stop
        self._lock = threading.Lock()
        self._sessions: dict[str, _Session] = {}

    def cameras(self) -> tuple[LabCamera, ...]:
        return lab_camera_definitions()

    def camera(self, camera_id: str) -> LabCamera:
        for item in self.cameras():
            if item.camera_id == camera_id:
                return item
        raise LabCameraError("unknown_camera")

    def health(self, camera_id: str) -> LabCameraHealth:
        camera = self.camera(camera_id)
        with self._lock:
            session = self._sessions.get(camera_id)
            if session is None:
                return LabCameraHealth(
                    camera.camera_id,
                    camera.name,
                    camera.host,
                    camera.source_id,
                    "idle",
                )
            return session.health(camera)

    def _notify(self, hook: object | None, camera_id: str) -> None:
        if hook is None:
            return
        try:
            hook(camera_id)
        except Exception:
            logging.getLogger("ilka.detection").exception(
                "camera preview hook failed for %s", camera_id
            )

    def acquire(self, camera_id: str) -> None:
        camera = self.camera(camera_id)
        started = False
        with self._lock:
            session = self._sessions.get(camera_id)
            if session is None:
                session = _Session(camera, self._opener, self._encoder)
                self._sessions[camera_id] = session
                session.start()
                started = True
            session.clients += 1
        if started:
            self._notify(self._on_start, camera_id)

    def release(self, camera_id: str) -> None:
        stopped = False
        with self._lock:
            session = self._sessions.get(camera_id)
            if session is None:
                return
            session.clients = max(0, session.clients - 1)
            if session.clients == 0:
                session.stop()
                self._sessions.pop(camera_id, None)
                stopped = True
        if stopped:
            self._notify(self._on_stop, camera_id)

    def latest_frame(self, camera_id: str) -> SharedFrame | None:
        camera = self.camera(camera_id)
        with self._lock:
            session = self._sessions.get(camera_id)
        if session is None:
            return None
        return session.latest_frame(camera)

    def latest_jpeg(self, camera_id: str) -> tuple[int, bytes | None, datetime | None]:
        with self._lock:
            session = self._sessions.get(camera_id)
            if session is None:
                return 0, None, None
            return session.sequence, session.jpeg, session.last_frame_at

    def multipart(self, camera_id: str):
        self.acquire(camera_id)
        try:
            seen = -1
            while True:
                sequence, payload, _moment = self.latest_jpeg(camera_id)
                if payload is not None and sequence != seen:
                    seen = sequence
                    header = (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(payload)).encode("ascii") + b"\r\n\r\n"
                    )
                    yield header + payload + b"\r\n"
                time.sleep(0.05)
        finally:
            self.release(camera_id)


class _Session:
    def __init__(self, camera: LabCamera, opener: object, encoder: object) -> None:
        self.camera = camera
        self._opener = opener
        self._encoder = encoder
        self.clients = 0
        self.state = "connecting"
        self.error: str | None = None
        self.jpeg: bytes | None = None
        self.sequence = 0
        self.last_frame_at: datetime | None = None
        self.width: int | None = None
        self.height: int | None = None
        self._frame_lock = threading.Lock()
        self._raw: object | None = None
        self._raw_at: datetime | None = None
        self._raw_sequence = 0
        self._raw_width: int | None = None
        self._raw_height: int | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name=f"lab-camera-{camera.camera_id}",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)

    def publish_frame(
        self,
        image: object,
        captured_at: datetime,
        width: int | None,
        height: int | None,
    ) -> None:
        copied = copy_image(image)
        with self._frame_lock:
            self._raw = copied
            self._raw_at = captured_at
            self._raw_sequence += 1
            self._raw_width = width
            self._raw_height = height

    def latest_frame(self, camera: LabCamera) -> SharedFrame | None:
        with self._frame_lock:
            raw = self._raw
            if raw is None or self._raw_at is None:
                return None
            sequence = self._raw_sequence
            captured_at = self._raw_at
            width = self._raw_width
            height = self._raw_height
        return SharedFrame(
            camera_id=camera.camera_id,
            sequence=sequence,
            captured_at=captured_at,
            width=width,
            height=height,
            data=copy_image(raw),
        )

    def health(self, camera: LabCamera) -> LabCameraHealth:
        return LabCameraHealth(
            camera.camera_id,
            camera.name,
            camera.host,
            camera.source_id,
            self.state,
            self.last_frame_at,
            self.width,
            self.height,
            self.error,
        )

    def _run(self) -> None:
        while not self._stop.is_set():
            source = None
            try:
                self.state = "connecting"
                self.error = None
                source = self._opener(self.camera)
                self.state = "live"
                while not self._stop.is_set():
                    frame = source.read()
                    if getattr(frame, "source_id", None) != self.camera.source_id:
                        raise LabCameraError("source_mismatch")
                    if getattr(frame, "is_synthetic", True):
                        raise LabCameraError("synthetic_frame")
                    shape = getattr(frame.data, "shape", None)
                    width = int(shape[1]) if shape and len(shape) >= 2 else None
                    height = int(shape[0]) if shape and len(shape) >= 2 else None
                    captured_at = getattr(frame, "captured_at", None) or datetime.now(UTC)
                    self.publish_frame(frame.data, captured_at, width, height)
                    payload = self._encoder(frame.data)
                    self.jpeg = payload
                    self.sequence += 1
                    self.last_frame_at = datetime.now(UTC)
                    self.width = width
                    self.height = height
            except Exception:
                self.state = "disconnected"
                self.error = "camera stream unavailable"
                self._stop.wait(0.5)
            finally:
                if source is not None:
                    source.close()


_hub: LabCameraHub | None = None
_hub_lock = threading.Lock()


def get_lab_camera_hub() -> LabCameraHub:
    global _hub
    with _hub_lock:
        if _hub is None:
            on_start = None
            on_stop = None
            if get_settings().environment != "testing":
                from app.services.person_preview import start_person_preview, stop_person_preview

                on_start = start_person_preview
                on_stop = stop_person_preview
            _hub = LabCameraHub(on_start=on_start, on_stop=on_stop)
        return _hub


def lab_cameras_available() -> bool:
    settings = get_settings()
    if settings.environment == "production":
        return False
    return bool(settings.lab_cameras_enabled)
