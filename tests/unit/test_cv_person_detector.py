from __future__ import annotations

import hashlib
import importlib.util
import os
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cv.detectors.base import PersonDetector
from cv.detectors.person_cpu import (
    MODEL_ID,
    WEIGHTS_SHA256,
    CpuPersonDetector,
    sha256_file,
)
from cv.errors import (
    DetectorDependencyError,
    DetectorInferenceError,
    DetectorModelError,
)
from cv.frame import MOCK_SYNTHETIC_LABEL, Frame


class _FakeImage:
    def __init__(self, height: int = 24, width: int = 32) -> None:
        self.shape = (height, width, 3)


def _frame() -> Frame:
    now = datetime.now(UTC)
    return Frame(
        data=_FakeImage(),
        index=0,
        captured_at=now,
        processed_at=now,
        source_id="lab-file",
    )


def test_cpu_person_detector_matches_protocol() -> None:
    detector = CpuPersonDetector(model=object())
    assert isinstance(detector, PersonDetector)
    assert detector.model_id == MODEL_ID


def test_min_confidence_default_and_bounds() -> None:
    detector = CpuPersonDetector(model=object())
    assert detector.min_confidence == 0.25
    with pytest.raises(ValueError, match="min_confidence"):
        CpuPersonDetector(model=object(), min_confidence=-0.01)
    with pytest.raises(ValueError, match="min_confidence"):
        CpuPersonDetector(model=object(), min_confidence=1.01)


def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _blocked(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("network access")

    monkeypatch.setattr(urllib.request, "urlopen", _blocked)


def test_missing_weights_path_raises_before_download(tmp_path: Path) -> None:
    missing = tmp_path / "missing.pth"
    with pytest.raises(DetectorModelError, match="do not exist"):
        CpuPersonDetector(weights_path=missing)


def test_weights_directory_is_not_a_file(tmp_path: Path) -> None:
    with pytest.raises(DetectorModelError, match="not a file"):
        CpuPersonDetector(weights_path=tmp_path)


def test_absent_weights_do_not_touch_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ILKA_CV_PERSON_WEIGHTS", raising=False)
    _block_network(monkeypatch)
    with pytest.raises(DetectorModelError, match="not configured"):
        CpuPersonDetector()


def test_unreadable_weights_raise(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "locked.pth"
    path.write_bytes(b"weights")

    def _denied(self: Path, *_args: object, **_kwargs: object) -> object:
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "open", _denied)
    with pytest.raises(DetectorModelError, match="unreadable"):
        CpuPersonDetector(weights_path=path)


def test_mismatched_checksum_raises_before_load(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "wrong.pth"
    path.write_bytes(b"not-the-official-artifact")
    _block_network(monkeypatch)

    def _unexpected_load(self: CpuPersonDetector) -> tuple[object, str]:
        raise AssertionError("state dict loaded")

    monkeypatch.setattr(CpuPersonDetector, "_load_model", _unexpected_load)
    with pytest.raises(DetectorModelError, match="checksum"):
        CpuPersonDetector(weights_path=path)
    assert sha256_file(path) != WEIGHTS_SHA256


def test_matching_checksum_is_accepted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    payload = b"provisional-lab-bytes"
    path = tmp_path / "ok.pth"
    path.write_bytes(payload)
    monkeypatch.setattr(
        "cv.detectors.person_cpu.WEIGHTS_SHA256",
        hashlib.sha256(payload).hexdigest(),
    )
    _block_network(monkeypatch)
    monkeypatch.setattr(CpuPersonDetector, "_load_model", lambda self: (object(), "unit-stub"))
    detector = CpuPersonDetector(weights_path=path)
    assert detector.model_version == "unit-stub"


def test_missing_torch_is_explicit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    payload = b"weights"
    path = tmp_path / "weights.pth"
    path.write_bytes(payload)
    monkeypatch.setattr(
        "cv.detectors.person_cpu.WEIGHTS_SHA256",
        hashlib.sha256(payload).hexdigest(),
    )

    def _boom() -> object:
        raise DetectorDependencyError("PyTorch is required")

    monkeypatch.setattr("cv.detectors.person_cpu._load_torch", _boom)
    with pytest.raises(DetectorDependencyError, match="PyTorch is required"):
        CpuPersonDetector(weights_path=path)


def test_benchmark_without_weights_does_not_download(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ILKA_CV_PERSON_WEIGHTS", raising=False)
    _block_network(monkeypatch)
    path = Path(__file__).resolve().parents[2] / "scripts" / "dev" / "bench_cpu_person_detector.py"
    spec = importlib.util.spec_from_file_location("ilka_bench_cpu_person_detector", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main() == 1


def test_detect_uses_mapping_without_real_weights(monkeypatch: pytest.MonkeyPatch) -> None:
    detector = CpuPersonDetector(model=object(), camera_id="cam-lab", min_confidence=0.25)

    def _fake_infer(_frame: Frame) -> tuple[list[object], list[object], list[object]]:
        return (
            [[2, 2, 20, 20], [2, 2, 20, 20], [0, 0, 1, 1]],
            [1, 8, 1],
            [0.8, 0.99, 0.1],
        )

    monkeypatch.setattr(detector, "_infer", _fake_infer)
    frame = _frame()
    rows = detector.detect(frame)
    assert len(rows) == 1
    item = rows[0]
    assert item.object_class == "person"
    assert item.confidence == 0.8
    assert item.source_id == "lab-file"
    assert item.camera_id == "cam-lab"
    assert item.track_id is None
    assert item.media_timestamp == frame.captured_at
    assert item.observed_at.tzinfo is not None
    assert item.is_synthetic is True
    assert item.mock_label == MOCK_SYNTHETIC_LABEL
    assert item.model_id == MODEL_ID


def test_detect_rejects_frame_without_shape() -> None:
    detector = CpuPersonDetector(model=object())
    frame = _frame()
    object.__setattr__(frame, "data", b"not-an-image")
    with pytest.raises(DetectorInferenceError, match="spatial shape"):
        detector.detect(frame)


def test_infer_wraps_model_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Boom:
        def __call__(self, _images: object) -> object:
            raise RuntimeError("forward failed")

    class _Torch:
        def inference_mode(self) -> object:
            from contextlib import nullcontext

            return nullcontext()

    detector = CpuPersonDetector(model=_Boom())
    monkeypatch.setattr(detector, "_frame_to_cpu_tensor", lambda _frame: object())
    monkeypatch.setattr("cv.detectors.person_cpu._load_torch", lambda: _Torch())
    with pytest.raises(DetectorInferenceError, match="inference failed"):
        detector.detect(_frame())


def test_mismatched_model_output_is_inference_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Bad:
        def __call__(self, _images: object) -> list[dict[str, list[int]]]:
            return [{"boxes": [[0, 0, 1, 1]], "labels": [1, 1], "scores": [1]}]

    class _Torch:
        def inference_mode(self) -> object:
            from contextlib import nullcontext

            return nullcontext()

    detector = CpuPersonDetector(model=_Bad())
    monkeypatch.setattr(detector, "_frame_to_cpu_tensor", lambda _frame: object())
    monkeypatch.setattr("cv.detectors.person_cpu._load_torch", lambda: _Torch())
    with pytest.raises(DetectorInferenceError, match="lengths do not match"):
        detector.detect(_frame())


def _live_detector_available() -> bool:
    import importlib.util

    if importlib.util.find_spec("torch") is None:
        return False
    if importlib.util.find_spec("torchvision") is None:
        return False
    raw = os.environ.get("ILKA_CV_PERSON_WEIGHTS", "").strip()
    if not raw:
        return False
    path = Path(raw)
    if not path.is_file():
        return False
    try:
        return sha256_file(path) == WEIGHTS_SHA256
    except DetectorModelError:
        return False


@pytest.mark.skipif(
    not _live_detector_available(),
    reason="optional Torch/TorchVision weights not configured (no download in tests)",
)
def test_live_cpu_detector_returns_observations_only() -> None:
    detector = CpuPersonDetector()
    assert detector.model_id == MODEL_ID
    frame = _frame()
    # Live path still requires HWC array conversion; skip if numpy missing.
    pytest.importorskip("numpy")
    import numpy as np

    object.__setattr__(frame, "data", np.zeros((24, 32, 3), dtype=np.uint8))
    rows = detector.detect(frame)
    for item in rows:
        assert item.object_class == "person"
        assert 0.0 <= item.confidence <= 1.0
        assert item.track_id is None
        assert item.model_id == MODEL_ID
