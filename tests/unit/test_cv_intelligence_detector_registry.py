from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from cv.detectors import registry as registry_module
from cv.detectors import yolo_optional
from cv.detectors.person_cpu import CpuPersonDetector
from cv.detectors.registry import (
    DEFAULT_DETECTOR,
    YOLO_DETECTOR,
    DetectorRegistry,
    default_registry,
    select_detector,
)
from cv.detectors.yolo_optional import WEIGHTS_ENV, YoloPersonDetector
from cv.errors import DetectorDependencyError
from cv.frame import Frame

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def _frame() -> Frame:
    return Frame(
        data=SimpleNamespace(shape=(100, 200, 3)),
        index=0,
        captured_at=NOW,
        processed_at=NOW,
        source_id="file:demo.mp4",
    )


def test_default_registry_lists_both_detectors() -> None:
    registry = default_registry()
    assert registry.names() == [DEFAULT_DETECTOR, YOLO_DETECTOR]
    assert registry.default == DEFAULT_DETECTOR


def test_availability_reports_reasons_without_loading(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(WEIGHTS_ENV, raising=False)
    monkeypatch.delenv("ILKA_CV_PERSON_WEIGHTS", raising=False)
    rows = {row.name: row for row in default_registry().availability()}
    assert rows[YOLO_DETECTOR].available is False
    assert rows[YOLO_DETECTOR].reason
    assert rows[DEFAULT_DETECTOR].default is True
    assert rows[DEFAULT_DETECTOR].available is False


def test_select_default_builds_existing_cpu_detector() -> None:
    detector = select_detector(model=object(), model_version="stub")
    assert isinstance(detector, CpuPersonDetector)
    assert detector.model_version == "stub"


def test_unknown_detector_name_raises_key_error() -> None:
    with pytest.raises(KeyError, match="unknown detector"):
        select_detector("does-not-exist")


def test_duplicate_registration_rejected() -> None:
    registry = DetectorRegistry()
    registry.register("a", model_id="a", factory=lambda **_: None)  # type: ignore[arg-type,return-value]
    with pytest.raises(ValueError, match="already"):
        registry.register("A", model_id="a", factory=lambda **_: None)  # type: ignore[arg-type,return-value]


def test_yolo_without_runtime_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(yolo_optional, "yolo_runtime_available", lambda: False)
    with pytest.raises(DetectorDependencyError, match="ultralytics"):
        select_detector(YOLO_DETECTOR)


def test_yolo_without_weights_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    monkeypatch.setattr(yolo_optional, "yolo_runtime_available", lambda: True)
    monkeypatch.delenv(WEIGHTS_ENV, raising=False)
    with pytest.raises(DetectorDependencyError, match="not configured"):
        YoloPersonDetector()
    monkeypatch.setenv(WEIGHTS_ENV, "/nonexistent/yolo.pt")
    with pytest.raises(DetectorDependencyError, match="does not exist"):
        YoloPersonDetector()


def test_yolo_availability_requires_weights_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    monkeypatch.setattr(registry_module, "_module_missing", lambda *names: None)
    monkeypatch.setenv(WEIGHTS_ENV, "/nonexistent/yolo.pt")
    rows = {row.name: row for row in default_registry().availability()}
    assert rows[YOLO_DETECTOR].available is False
    assert "does not point" in rows[YOLO_DETECTOR].reason


class _StubYolo:
    def predict(self, data: object, **kwargs: object) -> list[object]:
        assert kwargs["device"] == "cpu"
        boxes = SimpleNamespace(
            xyxy=[[20.0, 10.0, 60.0, 90.0], [100.0, 10.0, 150.0, 90.0]],
            cls=[0, 2],
            conf=[0.9, 0.95],
        )
        return [SimpleNamespace(boxes=boxes)]


def test_yolo_stub_maps_only_person_class() -> None:
    detector = YoloPersonDetector(model=_StubYolo(), model_version="stub", camera_id="cam-a")
    observations = detector.detect(_frame())
    assert len(observations) == 1
    observation = observations[0]
    assert observation.object_class == "person"
    assert observation.camera_id == "cam-a"
    assert observation.model_id == "ultralytics-yolo"
    assert observation.bounding_box.x_min == pytest.approx(0.1)
    assert observation.is_synthetic is True
