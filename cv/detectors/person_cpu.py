"""Optional CPU person detector. PROVISIONAL lab adapter, not a production model ADR.

TorchVision SSDLite320 MobileNetV3-Large (COCO). Inference is CPU-only.
Weights are never imported by the FastAPI backend and are never downloaded
from this constructor. This module does not certify detection accuracy.
"""

from __future__ import annotations

import hashlib
import os
from math import isfinite
from pathlib import Path
from types import ModuleType
from typing import Any

from cv.detectors.mapping import detections_to_observations
from cv.errors import (
    DetectorDependencyError,
    DetectorInferenceError,
    DetectorModelError,
)
from cv.frame import Frame
from cv.observation import Observation

MODEL_ID = "torchvision-ssdlite320-mobilenet-v3-large"
WEIGHTS_ENV = "ILKA_CV_PERSON_WEIGHTS"
DEFAULT_MIN_CONFIDENCE = 0.25
_CPU = "cpu"

# Official TorchVision COCO_V1 artifact. The filename prefix is the SHA-256 prefix
# torch.hub checks (hash_prefix) when TorchVision loads these weights with
# check_hash=True. PyTorch does not publish the full digest separately. The pin
# below is the SHA-256 of that URL after the prefix matched and the byte size
# matched TorchVision meta _file_size (13.418 MiB, 14069355 bytes).
WEIGHTS_ENUM = "SSDLite320_MobileNet_V3_Large_Weights.COCO_V1"
WEIGHTS_FILE = "ssdlite320_mobilenet_v3_large_coco-a79551df.pth"
WEIGHTS_URL = "https://download.pytorch.org/models/" + WEIGHTS_FILE
WEIGHTS_SHA256 = "a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2"
WEIGHTS_BYTES = 14_069_355


def _load_torch() -> ModuleType:
    try:
        import torch
    except ImportError as exc:
        raise DetectorDependencyError(
            "PyTorch is required for CpuPersonDetector. Install optional "
            "`cv/requirements-detector.txt` (CPU wheels; not a backend dependency)."
        ) from exc
    return torch


def _load_torchvision_detection() -> ModuleType:
    try:
        from torchvision.models import detection
    except ImportError as exc:
        raise DetectorDependencyError(
            "TorchVision is required for CpuPersonDetector. Install optional "
            "`cv/requirements-detector.txt` (CPU wheels; not a backend dependency)."
        ) from exc
    return detection


def sha256_file(path: Path) -> str:
    """Hash a local weights file. Does not open a network connection."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise DetectorModelError(f"person detector weights are unreadable: {path.name}") from exc
    return digest.hexdigest()


def verify_weights_file(path: Path, *, expected_sha256: str | None = None) -> str:
    """Fail closed unless the local file matches the pinned SHA-256."""
    expected = WEIGHTS_SHA256 if expected_sha256 is None else expected_sha256
    if not path.exists():
        raise DetectorModelError(f"person detector weights do not exist: {path.name}")
    if not path.is_file():
        raise DetectorModelError(f"person detector weights path is not a file: {path.name}")
    actual = sha256_file(path)
    if actual != expected:
        raise DetectorModelError(f"person detector weights checksum does not match: {path.name}")
    return actual


def _resolve_weights_path(weights_path: str | Path | None) -> Path:
    resolved = weights_path if weights_path is not None else os.environ.get(WEIGHTS_ENV)
    if isinstance(resolved, str):
        resolved = resolved.strip()
    if not resolved:
        raise DetectorModelError(
            "person detector weights are not configured. "
            f"Pass weights_path or set {WEIGHTS_ENV}. "
            "CpuPersonDetector does not download weights."
        )
    return Path(resolved)


def _finite_confidence(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    number = float(value)
    if not isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    if number < 0.0 or number > 1.0:
        raise ValueError(f"{name} must be in [0.0, 1.0]")
    return number


def _to_cpu_list(value: Any) -> list[Any]:
    if hasattr(value, "detach"):
        value = value.detach().to(_CPU).tolist()
    if isinstance(value, list):
        return value
    return list(value)


class CpuPersonDetector:
    """SSDLite320 MobileNetV3-Large on CPU. Emits M2 observations, not incidents."""

    model_id: str
    model_version: str

    def __init__(
        self,
        *,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
        camera_id: str | None = None,
        weights_path: str | Path | None = None,
        model: Any | None = None,
        model_version: str | None = None,
    ) -> None:
        self.min_confidence = _finite_confidence(min_confidence, "min_confidence")
        self.camera_id = camera_id
        self.model_id = MODEL_ID
        if model is not None:
            self._weights_path = None
            self._model = model
            self.model_version = model_version or "test-stub"
            return
        self._weights_path = _resolve_weights_path(weights_path)
        verify_weights_file(self._weights_path)
        self._model, self.model_version = self._load_model()

    def _load_model(self) -> tuple[Any, str]:
        if self._weights_path is None:
            raise DetectorModelError(
                "person detector weights are not configured. "
                f"Pass weights_path or set {WEIGHTS_ENV}."
            )
        torch = _load_torch()
        detection = _load_torchvision_detection()
        try:
            import torchvision
        except ImportError as exc:
            raise DetectorDependencyError(
                "TorchVision is required for CpuPersonDetector. Install optional "
                "`cv/requirements-detector.txt`."
            ) from exc
        version = str(getattr(torchvision, "__version__", "unknown"))
        builder = detection.ssdlite320_mobilenet_v3_large
        path = self._weights_path
        try:
            model = builder(weights=None, weights_backbone=None)
            state = torch.load(path, map_location=_CPU, weights_only=True)
            if isinstance(state, dict) and "state_dict" in state:
                state = state["state_dict"]
            if not isinstance(state, dict):
                raise DetectorModelError("person detector weights must be a state dict")
            model.load_state_dict(state)
        except DetectorModelError:
            raise
        except Exception as exc:
            raise DetectorModelError("person detector weights could not be loaded") from exc
        model.to(_CPU)
        model.eval()
        return model, version

    def _frame_to_cpu_tensor(self, frame: Frame) -> Any:
        torch = _load_torch()
        data = frame.data
        shape = getattr(data, "shape", None)
        if shape is None or len(shape) < 3 or int(shape[2]) < 3:
            raise DetectorInferenceError("frame data must be an HWC image with at least 3 channels")
        height, width = int(shape[0]), int(shape[1])
        if height < 1 or width < 1:
            raise DetectorInferenceError("frame spatial size is invalid")
        try:
            import numpy as np
        except ImportError as exc:
            raise DetectorDependencyError(
                "NumPy is required to convert frames for CpuPersonDetector."
            ) from exc
        try:
            array = np.asarray(data)
            rgb = np.ascontiguousarray(array[:, :, :3][:, :, ::-1])
            tensor = torch.from_numpy(rgb).permute(2, 0, 1).to(device=_CPU, dtype=torch.float32)
            tensor = tensor / 255.0
        except DetectorInferenceError:
            raise
        except Exception as exc:
            raise DetectorInferenceError("frame could not be converted for CPU inference") from exc
        return tensor

    def _infer(self, frame: Frame) -> tuple[list[Any], list[Any], list[Any]]:
        try:
            tensor = self._frame_to_cpu_tensor(frame)
            torch = _load_torch()
            with torch.inference_mode():
                raw = self._model([tensor])
            if not raw:
                raise DetectorInferenceError("person detector returned no output")
            first = raw[0]
            boxes = _to_cpu_list(first["boxes"])
            labels = _to_cpu_list(first["labels"])
            scores = _to_cpu_list(first["scores"])
        except (DetectorDependencyError, DetectorInferenceError):
            raise
        except Exception as exc:
            raise DetectorInferenceError("person detector inference failed") from exc
        if not (len(boxes) == len(labels) == len(scores)):
            raise DetectorInferenceError("person detector output lengths do not match")
        return boxes, labels, scores

    def detect(self, frame: Frame) -> list[Observation]:
        shape = getattr(frame.data, "shape", None)
        if shape is None or len(shape) < 2:
            raise DetectorInferenceError("frame data must have a spatial shape")
        height, width = int(shape[0]), int(shape[1])
        boxes, labels, scores = self._infer(frame)
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
            raise DetectorInferenceError("person detector outputs could not be mapped") from exc
