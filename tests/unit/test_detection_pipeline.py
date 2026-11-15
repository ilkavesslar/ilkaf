from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from cv.errors import DetectorInferenceError
from cv.frame import Frame
from cv.observation import BoundingBox, Observation
from cv.pipeline import run_sampled_detection
from cv.streams.file import FileSource


class _Source:
    source_id = "fake"

    def __init__(self, count: int) -> None:
        self._left = count

    def read(self) -> Frame | None:
        if self._left <= 0:
            return None
        index = 4 - self._left
        self._left -= 1
        now = datetime(2026, 11, 8, tzinfo=UTC)
        return Frame(
            data=b"frame",
            index=index,
            captured_at=now,
            processed_at=now,
            source_id=self.source_id,
        )


class _Detector:
    model_id = "stub"
    model_version = "0"
    calls = 0

    def detect(self, frame: Frame) -> list[Observation]:
        self.calls += 1
        now = datetime(2026, 11, 8, tzinfo=UTC)
        return [
            Observation(
                observation_id=uuid4(),
                source_id=frame.source_id,
                object_class="person",
                confidence=0.5,
                bounding_box=BoundingBox(0.1, 0.1, 0.2, 0.2),
                model_id=self.model_id,
                model_version=self.model_version,
                observed_at=now,
            )
        ]


def test_sampled_detection_skips_frames_and_does_not_invent_incidents() -> None:
    detector = _Detector()
    result = run_sampled_detection(_Source(4), detector, max_frames=4, sample_every=2)
    assert result.frames_read == 4
    assert result.frames_inferred == 2
    assert detector.calls == 2
    assert len(result.observations) == 2
    assert all(item.object_class == "person" for item in result.observations)


def test_detector_failure_hides_the_original_message() -> None:
    class Broken:
        model_id = "stub"
        model_version = "0"

        def detect(self, frame: Frame) -> list[Observation]:
            del frame
            raise RuntimeError("rtsp://user:secret@192.168.1.17/stream")

    with pytest.raises(DetectorInferenceError) as caught:
        run_sampled_detection(_Source(1), Broken(), max_frames=1)
    assert str(caught.value) == "detection failed"
    assert "secret" not in str(caught.value)


def test_sampled_detection_reads_a_bounded_local_file() -> None:
    pytest.importorskip("cv2")
    video = Path(__file__).resolve().parents[2] / "data" / "videos" / "people-detection (1).mp4"
    if not video.is_file():
        pytest.skip("local demo video is not present")

    class Stub:
        model_id = "stub"
        model_version = "0"

        def detect(self, frame: Frame) -> list[Observation]:
            del frame
            return []

    with FileSource(video, source_id="local-file") as source:
        result = run_sampled_detection(source, Stub(), max_frames=2, sample_every=1)
    assert result.frames_read == 2
    assert result.frames_inferred == 2
    assert result.observations == []
