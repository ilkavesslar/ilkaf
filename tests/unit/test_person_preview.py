from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.services.detection_state import get_detection_state
from app.services.lab_camera_streams import LabCameraHub, SharedFrame
from app.services.person_preview import (
    PersonPreviewSupervisor,
    PersonPreviewWorker,
    _CameraActivity,
)

from cv.frame import Frame
from cv.observation import BoundingBox, Observation


def _shared(sequence: int, camera_id: str = "camera-1") -> SharedFrame:
    return SharedFrame(
        camera_id=camera_id,
        sequence=sequence,
        captured_at=datetime(2026, 11, 8, tzinfo=UTC),
        width=2,
        height=2,
        data=b"frame",
    )


def _observation() -> Observation:
    return Observation(
        observation_id=uuid4(),
        source_id="camera-1",
        object_class="person",
        confidence=0.4,
        bounding_box=BoundingBox(0.1, 0.1, 0.2, 0.2),
        model_id="stub",
        model_version="0",
        observed_at=datetime(2026, 11, 8, tzinfo=UTC),
    )


def _wait_until(predicate, timeout: float = 1.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("condition was not met")


def test_preview_hooks_follow_the_reader_lifecycle() -> None:
    started: list[str] = []
    stopped: list[str] = []
    hub = LabCameraHub(
        opener=lambda camera: _Quiet(camera),
        encoder=lambda image: b"jpeg",
        on_start=started.append,
        on_stop=stopped.append,
    )
    camera_id = "vigi-c320i-192.168.1.17"
    hub.acquire(camera_id)
    hub.acquire(camera_id)
    assert started == [camera_id]
    hub.release(camera_id)
    assert stopped == []
    hub.release(camera_id)
    assert stopped == [camera_id]


class _Quiet:
    def __init__(self, camera: object) -> None:
        self.source_id = camera.source_id
        self.closed = 0

    def read(self) -> object:
        time.sleep(0.05)
        raise RuntimeError("stop the reader")

    def close(self) -> None:
        self.closed += 1


def test_one_worker_samples_a_copied_frame_and_stops_cleanly() -> None:
    get_detection_state().clear()
    calls = {"count": 0}

    def detect(frame: Frame) -> list[Observation]:
        calls["count"] += 1
        assert frame.source_id == "camera-1"
        return [_observation()]

    worker = PersonPreviewWorker(
        "camera-1",
        frames=lambda camera_id: _shared(1, camera_id),
        detect=detect,
        interval_s=30,
    )
    supervisor = PersonPreviewSupervisor()
    first = supervisor.start("camera-1", worker)
    second = supervisor.start("camera-1")
    assert first is second
    _wait_until(lambda: get_detection_state().read("camera-1") is not None)
    assert calls["count"] == 1
    sample = get_detection_state().read("camera-1")
    assert sample is not None
    assert sample.status == "ready"
    assert sample.items[0].camera_id == "camera-1"
    assert sample.items[0].track_id == 1
    assert sample.items[0].moving is False
    assert sample.items[0].waving is False
    supervisor.stop("camera-1")
    assert get_detection_state().read("camera-1") is None
    assert not worker.alive()


def test_missing_frame_clears_the_last_observation() -> None:
    get_detection_state().clear()
    frames: dict[str, SharedFrame | None] = {"value": _shared(1)}
    worker = PersonPreviewWorker(
        "camera-1",
        frames=lambda camera_id: frames["value"],
        detect=lambda frame: [_observation()],
        interval_s=30,
    )
    worker.start()
    try:
        _wait_until(lambda: get_detection_state().read("camera-1") is not None)
        frames["value"] = None
        _wait_until(lambda: get_detection_state().read("camera-1") is None)
    finally:
        worker.stop()
        get_detection_state().clear()


def test_detector_failure_stays_on_that_camera() -> None:
    get_detection_state().clear()

    def explode(frame: Frame) -> list[Observation]:
        del frame
        raise RuntimeError("rtsp://user:secret@192.168.1.17/stream")

    def healthy(frame: Frame) -> list[Observation]:
        del frame
        return []

    failed = PersonPreviewWorker(
        "camera-1",
        frames=lambda camera_id: _shared(1, camera_id),
        detect=explode,
        interval_s=30,
    )
    other = PersonPreviewWorker(
        "camera-2",
        frames=lambda camera_id: _shared(1, camera_id),
        detect=healthy,
        interval_s=30,
    )
    failed.start()
    other.start()
    try:
        _wait_until(
            lambda: (sample := get_detection_state().read("camera-1")) is not None
            and sample.status == "error"
        )
        _wait_until(
            lambda: (sample := get_detection_state().read("camera-2")) is not None
            and sample.status == "ready"
        )
        broken = get_detection_state().read("camera-1")
        assert broken is not None
        assert broken.detail == "Person detection failed."
        assert "secret" not in broken.detail
        assert broken.items == []
        ready = get_detection_state().read("camera-2")
        assert ready is not None
        assert ready.detail == "No active observations."
    finally:
        failed.stop()
        other.stop()
        get_detection_state().clear()


def _person(x_min: float, when: datetime, confidence: float = 0.94) -> Observation:
    return Observation(
        observation_id=uuid4(),
        source_id="camera-1",
        object_class="person",
        confidence=confidence,
        bounding_box=BoundingBox(x_min, 0.40, x_min + 0.10, 0.70),
        model_id="stub",
        model_version="0",
        observed_at=when,
    )


def _frame(when: datetime) -> Frame:
    return Frame(
        data=b"frame",
        index=1,
        captured_at=when,
        processed_at=when,
        source_id="camera-1",
        is_synthetic=False,
        source_kind="rtsp",
        mock_label="",
    )


def test_each_camera_keeps_its_own_track_numbers() -> None:
    moment = datetime(2026, 11, 13, tzinfo=UTC)
    left = _CameraActivity()
    right = _CameraActivity()
    left_items = left.observe("camera-1", [_person(0.20, moment)], _frame(moment))
    right_items = right.observe("camera-2", [_person(0.20, moment)], _frame(moment))
    assert left_items[0].track_id == 1
    assert right_items[0].track_id == 1
    assert left_items[0].moving is False
    assert left_items[0].waving is False


def test_small_motion_is_not_moving_and_sustained_motion_is() -> None:
    start = datetime(2026, 11, 13, tzinfo=UTC)
    activity = _CameraActivity()
    jitter = (0.45, 0.48, 0.45, 0.48)
    for index, x_min in enumerate(jitter):
        moment = start + timedelta(seconds=index)
        items = activity.observe("camera-1", [_person(x_min, moment)], _frame(moment))
    assert items[0].moving is False

    moving = _CameraActivity()
    for index, x_min in enumerate((0.05, 0.30, 0.55)):
        moment = start + timedelta(seconds=index)
        items = moving.observe("camera-1", [_person(x_min, moment)], _frame(moment))
    assert items[0].track_id == 1
    assert items[0].moving is True
    assert items[0].waving is False


def test_a_still_person_can_wave_without_moving() -> None:
    class _Wave:
        def __init__(self) -> None:
            self.step = 0

        def read(self, image: object) -> list[object]:
            del image
            wrist_x = 0.12 if self.step % 2 == 0 else 0.36
            self.step += 1
            from cv.gestures import PoseCue

            return [PoseCue(anchor=(0.25, 0.55), left_wrist=(wrist_x, 0.55), right_wrist=None)]

        def close(self) -> None:
            return None

    start = datetime(2026, 11, 13, tzinfo=UTC)
    activity = _CameraActivity(_Wave())
    items = []
    for index in range(4):
        moment = start + timedelta(seconds=index * 0.4)
        seen = Observation(
            observation_id=uuid4(),
            source_id="camera-1",
            object_class="person",
            confidence=0.91,
            bounding_box=BoundingBox(0.10, 0.40, 0.40, 0.80),
            model_id="stub",
            model_version="0",
            observed_at=moment,
        )
        items = activity.observe("camera-1", [seen], _frame(moment))
    assert items[0].moving is False
    assert items[0].waving is True


def test_stopping_a_worker_releases_its_pose_reader() -> None:
    class _Pose:
        def __init__(self) -> None:
            self.closed = False

        def read(self, image: object) -> list[object]:
            del image
            return []

        def close(self) -> None:
            self.closed = True

    pose = _Pose()
    get_detection_state().clear()
    worker = PersonPreviewWorker(
        "camera-1",
        frames=lambda camera_id: _shared(1, camera_id),
        detect=lambda frame: [_observation()],
        interval_s=30,
        activity=_CameraActivity(pose),
    )
    worker.start()
    try:
        _wait_until(lambda: get_detection_state().read("camera-1") is not None)
    finally:
        worker.stop()
    assert pose.closed is True
    assert get_detection_state().read("camera-1") is None
