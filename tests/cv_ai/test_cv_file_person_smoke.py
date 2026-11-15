from __future__ import annotations

import importlib.util
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cv.detectors.person_cpu import MODEL_ID, CpuPersonDetector
from cv.frame import MOCK_SYNTHETIC_LABEL
from cv.observation import Observation
from cv.streams.file import FileSource


def _write_color_clip(path: Path, frame_count: int = 6) -> None:
    """Same temp MJPG clip as ``test_cv_file_source`` (``tests.unit`` is not importable)."""
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


def _explicit_weights_file() -> Path | None:
    raw = os.environ.get("ILKA_CV_PERSON_WEIGHTS", "").strip()
    if not raw:
        return None
    path = Path(raw)
    if path.is_file():
        return path
    return None


def _optional_cpu_stack_ready() -> bool:
    if importlib.util.find_spec("torch") is None:
        return False
    if importlib.util.find_spec("torchvision") is None:
        return False
    return _explicit_weights_file() is not None


def _assert_observation(item: Observation, *, source_id: str, captured_at: datetime) -> None:
    assert isinstance(item, Observation)
    assert item.object_class == "person"
    assert item.confidence >= 0.25
    assert item.confidence <= 1.0
    box = item.bounding_box
    assert 0.0 <= box.x_min < box.x_max <= 1.0
    assert 0.0 <= box.y_min < box.y_max <= 1.0
    assert item.source_id == source_id
    assert item.media_timestamp == captured_at
    assert item.observed_at.tzinfo is not None
    assert item.is_synthetic is True
    assert item.mock_label == MOCK_SYNTHETIC_LABEL
    assert item.track_id is None
    assert item.model_id == MODEL_ID
    assert item.model_version
    assert item.model_version != "test-stub"


@pytest.mark.skipif(
    not _optional_cpu_stack_ready(),
    reason="live FileSource smoke needs CPU Torch/TorchVision and ILKA_CV_PERSON_WEIGHTS file",
)
def test_file_source_cpu_person_detector_smoke(tmp_path: Path) -> None:
    weights = _explicit_weights_file()
    assert weights is not None
    clip = tmp_path / "smoke.avi"
    _write_color_clip(clip, frame_count=4)
    origin = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    detector = CpuPersonDetector(weights_path=weights, min_confidence=0.25)
    assert detector.model_id == MODEL_ID
    assert detector.model_version != "test-stub"

    observations: list[Observation] = []
    with FileSource(clip, source_id="smoke-file", timeline_origin=origin) as source:
        while True:
            frame = source.read()
            if frame is None:
                break
            for item in detector.detect(frame):
                _assert_observation(
                    item,
                    source_id="smoke-file",
                    captured_at=frame.captured_at,
                )
                observations.append(item)

    assert isinstance(observations, list)
