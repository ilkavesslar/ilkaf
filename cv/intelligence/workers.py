"""Multi-camera worker helpers with bounded queues. Failures stay camera-local."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class WorkerStats:
    camera_id: str
    frames_enqueued: int
    frames_dropped: int
    frames_processed: int
    last_error: str | None


class CameraFrameWorker:
    """One camera worker. Keeps only the newest frame when the queue is full."""

    def __init__(
        self,
        camera_id: str,
        process: Callable[[Any], None],
        *,
        maxsize: int = 1,
    ) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        self.camera_id = camera_id
        self._process = process
        self._queue: queue.Queue[Any] = queue.Queue(maxsize=maxsize)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.frames_enqueued = 0
        self.frames_dropped = 0
        self.frames_processed = 0
        self.last_error: str | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"ilka-hie-{self.camera_id}",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout)

    def submit(self, frame: Any) -> bool:
        """Enqueue ``frame``. Returns False if an older frame was dropped."""

        self.frames_enqueued += 1
        dropped = False
        while True:
            try:
                self._queue.put_nowait(frame)
                return not dropped
            except queue.Full:
                try:
                    self._queue.get_nowait()
                    self.frames_dropped += 1
                    dropped = True
                except queue.Empty:
                    continue

    def stats(self) -> WorkerStats:
        return WorkerStats(
            camera_id=self.camera_id,
            frames_enqueued=self.frames_enqueued,
            frames_dropped=self.frames_dropped,
            frames_processed=self.frames_processed,
            last_error=self.last_error,
        )

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                frame = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                self._process(frame)
                self.frames_processed += 1
                self.last_error = None
            except Exception as exc:  # noqa: BLE001 — isolate camera failures
                self.last_error = f"{type(exc).__name__}: {exc}"
