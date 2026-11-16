from __future__ import annotations

import time

from cv.intelligence.workers import CameraFrameWorker


def test_camera_worker_keeps_newest_frame_under_backpressure() -> None:
    seen: list[int] = []

    def process(frame: int) -> None:
        seen.append(frame)
        time.sleep(0.05)

    worker = CameraFrameWorker("cam-a", process, maxsize=1)
    worker.start()
    try:
        worker.submit(1)
        time.sleep(0.02)
        worker.submit(2)
        worker.submit(3)
        time.sleep(0.2)
    finally:
        worker.stop()
    stats = worker.stats()
    assert stats.frames_enqueued == 3
    assert stats.frames_dropped >= 1
    assert 3 in seen
    assert stats.last_error is None
