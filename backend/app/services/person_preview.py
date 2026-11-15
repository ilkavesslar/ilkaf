"""Sample copied preview frames. Does not open RTSP or serve HTTP."""

from __future__ import annotations

import logging
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from cv.frame import Frame
from cv.gestures import GestureTracker, PoseCue, associate_cues, relative_x
from cv.movement import Movement, classify_movement
from cv.observation import Observation
from cv.pose_wrists import WristPoseReader
from cv.sampling import InferenceClock
from cv.tracking import PersonTracker, Track

from app.core.config import get_settings
from app.schemas.detection import LiveObservationItem
from app.services.detection_state import get_detection_state, to_live_observation
from app.services.lab_camera_streams import SharedFrame, get_lab_camera_hub

_LOG = logging.getLogger("ilka.detection")
_UNAVAILABLE = "Person detection is unavailable."
_FAILED = "Person detection failed."

_detector_lock = threading.Lock()
_detector: object | None = None
_detector_failed = False


def _as_frame(shared: SharedFrame) -> Frame:
    captured = shared.captured_at
    if captured.tzinfo is None:
        captured = captured.replace(tzinfo=UTC)
    return Frame(
        data=shared.data,
        index=shared.sequence,
        captured_at=captured,
        processed_at=datetime.now(UTC),
        source_id=shared.camera_id,
        is_synthetic=False,
        source_kind="rtsp",
        mock_label="",
    )


def _load_detector() -> object:
    global _detector, _detector_failed
    with _detector_lock:
        if _detector is not None:
            return _detector
        if _detector_failed:
            raise RuntimeError("person detector is unavailable")
        root = str(Path(__file__).resolve().parents[3])
        if root not in sys.path:
            sys.path.insert(0, root)
        try:
            from cv.capabilities import _weights_candidate
            from cv.detectors.person_cpu import CpuPersonDetector

            weights = _weights_candidate()
            if weights is None:
                raise RuntimeError("person detector weights are not configured")
            _detector = CpuPersonDetector(weights_path=weights)
        except Exception:
            _detector_failed = True
            _LOG.exception("person detector could not be loaded")
            raise
        return _detector


def _detect_frame(frame: Frame) -> list[Observation]:
    detector = _load_detector()
    with _detector_lock:
        return detector.detect(frame)  # type: ignore[attr-defined]


def _live_frame(camera_id: str) -> SharedFrame | None:
    hub = get_lab_camera_hub()
    if hub.health(camera_id).state != "live":
        return None
    return hub.latest_frame(camera_id)


def _open_pose() -> WristPoseReader | None:
    path = Path(__file__).resolve().parents[3] / "data" / "models" / "pose_landmarker_lite.task"
    reader = WristPoseReader(path)
    if reader.open():
        return reader
    return None


def _record_waves(
    gestures: GestureTracker,
    tracks: list[Track],
    cues: list[PoseCue],
    when: datetime,
) -> None:
    pairs = [(track.track_id, track.latest_observation.bounding_box) for track in tracks]
    assigned = associate_cues(pairs, cues)
    for track in tracks:
        cue = assigned.get(track.track_id)
        box = track.latest_observation.bounding_box
        left = relative_x(cue.left_wrist[0], box) if cue is not None and cue.left_wrist else None
        right = relative_x(cue.right_wrist[0], box) if cue is not None and cue.right_wrist else None
        gestures.update(track.track_id, when, left, right)


class _CameraActivity:
    """Tracker, movement, and waving for one camera. Not shared across cameras."""

    def __init__(self, pose: object | None = None) -> None:
        self.tracker = PersonTracker()
        self.movements: dict[int, Movement] = {}
        self.gestures = GestureTracker()
        self._pose = pose

    def close(self) -> None:
        pose = self._pose
        self._pose = None
        if pose is not None:
            pose.close()

    def observe(
        self,
        camera_id: str,
        found: list[Observation],
        frame: Frame,
    ) -> list[LiveObservationItem]:
        when = frame.processed_at
        tracks = self.tracker.update(found, when)
        active = {track.track_id for track in tracks}
        self.movements = {
            track.track_id: classify_movement(
                track.center_history,
                self.movements.get(track.track_id),
            )
            for track in tracks
        }
        _record_waves(self.gestures, tracks, self._cues(frame.data), when)
        self.gestures.retain(active)
        return [
            to_live_observation(
                track.latest_observation,
                camera_id,
                track_id=track.track_id,
                moving=self.movements.get(track.track_id) == "moving",
                waving=self.gestures.waving(track.track_id, when),
            )
            for track in tracks
        ]

    def _cues(self, image: object) -> list[PoseCue]:
        if self._pose is None:
            return []
        try:
            return self._pose.read(image)
        except Exception:
            _LOG.exception("wrist pose read failed")
            return []


class PersonPreviewWorker:
    """One inference thread for one camera preview. It reads copied frames only."""

    def __init__(
        self,
        camera_id: str,
        *,
        frames: object | None = None,
        detect: object | None = None,
        interval_s: float | None = None,
        activity: _CameraActivity | None = None,
    ) -> None:
        self.camera_id = camera_id
        self._frames = frames or _live_frame
        self._detect = detect or _detect_frame
        self._interval = (
            get_settings().detection_sample_interval_s if interval_s is None else interval_s
        )
        self._activity = activity
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_sequence = -1

    def alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"ilka-person-{self.camera_id}",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=2)
        get_detection_state().forget(self.camera_id)

    def _run(self) -> None:
        clock = InferenceClock(self._interval)
        activity = self._activity if self._activity is not None else _CameraActivity(_open_pose())
        try:
            while not self._stop.is_set():
                try:
                    shared = self._frames(self.camera_id)
                except Exception:
                    _LOG.exception("preview frame copy failed")
                    get_detection_state().publish_error(self.camera_id, _UNAVAILABLE)
                    if self._stop.wait(self._interval):
                        return
                    continue
                if shared is None:
                    self._last_sequence = -1
                    get_detection_state().forget(self.camera_id)
                    self._stop.wait(0.05)
                    continue
                if shared.sequence == self._last_sequence:
                    self._stop.wait(0.05)
                    continue
                if not clock.due(self.camera_id, time.monotonic()):
                    self._stop.wait(0.05)
                    continue
                self._last_sequence = shared.sequence
                frame = _as_frame(shared)
                try:
                    found = self._detect(frame)
                except Exception:
                    _LOG.exception("person sample failed")
                    get_detection_state().publish_error(self.camera_id, _FAILED)
                    continue
                get_detection_state().publish(
                    self.camera_id,
                    activity.observe(self.camera_id, found, frame),
                )
        finally:
            activity.close()


class PersonPreviewSupervisor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._workers: dict[str, PersonPreviewWorker] = {}

    def start(
        self,
        camera_id: str,
        worker: PersonPreviewWorker | None = None,
    ) -> PersonPreviewWorker:
        with self._lock:
            current = self._workers.get(camera_id)
            if current is not None and current.alive():
                return current
            created = worker or PersonPreviewWorker(camera_id)
            self._workers[camera_id] = created
        created.start()
        return created

    def stop(self, camera_id: str) -> None:
        with self._lock:
            worker = self._workers.pop(camera_id, None)
        if worker is not None:
            worker.stop()

    def stop_all(self) -> None:
        with self._lock:
            workers = list(self._workers.values())
            self._workers.clear()
        for worker in workers:
            worker.stop()


_supervisor = PersonPreviewSupervisor()


def start_person_preview(camera_id: str) -> None:
    _supervisor.start(camera_id)


def stop_person_preview(camera_id: str) -> None:
    _supervisor.stop(camera_id)


def stop_all_person_previews() -> None:
    _supervisor.stop_all()
