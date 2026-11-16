"""Optional Ultralytics YOLO person detector. EXPERIMENTAL, not a model ADR.

Fails closed: if the ``ultralytics`` runtime or a local weights file is
missing, construction raises ``DetectorDependencyError``. This adapter never
passes a bare model name to Ultralytics (which would download weights).
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

from cv.detectors.mapping import COCO_PERSON_LABEL, detections_to_observations
from cv.detectors.person_cpu import sha256_file
from cv.errors import DetectorDependencyError, DetectorInferenceError, DetectorModelError
from cv.frame import Frame
from cv.observation import Observation

MODEL_ID = "ultralytics-yolo"
WEIGHTS_ENV = "ILKA_CV_YOLO_WEIGHTS"
YOLO_PERSON_CLASS = 0
DEFAULT_MIN_CONFIDENCE = 0.25


def yolo_runtime_available() -> bool:
    return importlib.util.find_spec("ultralytics") is not None


def resolve_yolo_weights(weights_path: str | Path | None = None) -> Path:
    """Return an existing local weights file or raise ``DetectorDependencyError``."""

    resolved: str | Path | None = weights_path
    if resolved is None:
        resolved = os.environ.get(WEIGHTS_ENV)
    if isinstance(resolved, str):
        resolved = resolved.strip()
    if not resolved:
        raise DetectorDependencyError(
            f"YOLO weights are not configured. Pass weights_path or set {WEIGHTS_ENV}. "
            "The YOLO adapter does not download weights."
        )
    path = Path(resolved)
    if not path.is_file():
        raise DetectorDependencyError(f"YOLO weights file does not exist: {path.name}")
    return path


class YoloPersonDetector:
    """Ultralytics YOLO on CPU, person class only. Emits observations, not incidents."""

    model_id: str
    model_version: str

    def __init__(
        self,
        *,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
        camera_id: str | None = None,
        weights_path: str | Path | None = None,
        expected_sha256: str | None = None,
        model: Any | None = None,
        model_version: str | None = None,
    ) -> None:
        if isinstance(min_confidence, bool) or not 0.0 <= float(min_confidence) <= 1.0:
            raise ValueError("min_confidence must be in [0.0, 1.0]")
        self.min_confidence = float(min_confidence)
        self.camera_id = camera_id
        self.model_id = MODEL_ID
        if model is not None:
            self._model = model
            self.model_version = model_version or "test-stub"
            return
        if not yolo_runtime_available():
            raise DetectorDependencyError(
                "The `ultralytics` package is required for the YOLO detector. It is an "
                "optional, unpinned lab dependency and is not installed."
            )
        path = resolve_yolo_weights(weights_path)
        if expected_sha256 is not None and sha256_file(path) != expected_sha256:
            raise DetectorModelError(f"YOLO weights checksum does not match: {path.name}")
        try:
            from ultralytics import YOLO

            self._model = YOLO(str(path))
        except Exception as exc:
            raise DetectorModelError("YOLO weights could not be loaded") from exc
        try:
            import ultralytics

            version = str(getattr(ultralytics, "__version__", "unknown"))
        except ImportError:
            version = "unknown"
        self.model_version = model_version or f"{version}:{path.name}"

    def detect(self, frame: Frame) -> list[Observation]:
        shape = getattr(frame.data, "shape", None)
        if shape is None or len(shape) < 3 or int(shape[2]) < 3:
            raise DetectorInferenceError("frame data must be an HWC image with at least 3 channels")
        height, width = int(shape[0]), int(shape[1])
        try:
            results = self._model.predict(
                frame.data, device="cpu", verbose=False, conf=self.min_confidence
            )
            boxes: list[list[float]] = []
            labels: list[int] = []
            scores: list[float] = []
            for result in results or []:
                raw = result.boxes
                for xyxy, cls, conf in zip(
                    _as_list(raw.xyxy), _as_list(raw.cls), _as_list(raw.conf), strict=True
                ):
                    boxes.append([float(value) for value in xyxy])
                    labels.append(COCO_PERSON_LABEL if int(cls) == YOLO_PERSON_CLASS else -1)
                    scores.append(float(conf))
        except Exception as exc:
            raise DetectorInferenceError("YOLO inference failed") from exc
        try:
            return detections_to_observations(
                boxes=boxes,
                labels=labels,
                scores=scores,
                frame=frame,
                width=width,
                height=height,
                min_confidence=self.min_confidence,
                model_id=self.model_id,
                model_version=self.model_version,
                camera_id=self.camera_id,
            )
        except ValueError as exc:
            raise DetectorInferenceError("YOLO outputs could not be mapped") from exc


def _as_list(value: Any) -> list[Any]:
    if hasattr(value, "detach"):
        value = value.detach().to("cpu")
    if hasattr(value, "tolist"):
        return list(value.tolist())
    return list(value)
