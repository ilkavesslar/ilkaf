#!/usr/bin/env python3
"""CPU latency harness for the pinned SSDLite person detector.

Runs only when PyTorch, TorchVision, NumPy, and a local weights file are
already present. Otherwise it exits 0 and prints a skip reason. It never
downloads weights and never prints a fabricated latency or accuracy number.

A blank frame is ``[MOCK / SYNTHETIC]``. Detection counts on that frame are
not precision, recall, or a dataset result.
"""

from __future__ import annotations

import importlib.util
import os
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WEIGHTS_ENV = "ILKA_CV_PERSON_WEIGHTS"
DEFAULT_WEIGHTS = ROOT / "data" / "models" / "ssdlite320_mobilenet_v3_large_coco.pth"
DEFAULT_FRAMES = 8
DEFAULT_WARMUP = 1


def skip_reason(*, torch_available: bool, torchvision_available: bool, numpy_available: bool, weights_file: Path | None) -> str | None:
    """Return why a real measurement cannot run, or ``None`` when it can."""

    if not torch_available:
        return "PyTorch is not importable. This harness does not install it."
    if not torchvision_available:
        return "TorchVision is not importable. This harness does not install it."
    if not numpy_available:
        return "NumPy is not importable. This harness does not install it."
    if weights_file is None:
        return (
            f"No local SSDLite weights file. Set {WEIGHTS_ENV} to the pinned file "
            "or place it at data/models/ssdlite320_mobilenet_v3_large_coco.pth. "
            "This harness does not download weights."
        )
    if not weights_file.is_file():
        return (
            f"Weights path is not a file ({weights_file.name}). "
            "This harness does not download weights."
        )
    return None


def resolve_weights_file() -> Path | None:
    """Prefer ``ILKA_CV_PERSON_WEIGHTS``. Fall back to the documented local path."""

    configured = os.environ.get(WEIGHTS_ENV, "").strip()
    if configured:
        return Path(configured)
    if DEFAULT_WEIGHTS.is_file():
        return DEFAULT_WEIGHTS
    return None


def summarize_latency_ms(samples: list[float]) -> tuple[float, float]:
    """Median and nearest-rank p95. Empty input raises instead of inventing a time."""

    if not samples:
        raise ValueError("latency samples are empty; refusing to invent a timing")
    ordered = sorted(samples)
    p50 = statistics.median(ordered)
    p95 = ordered[max(0, round(0.95 * (len(ordered) - 1)))]
    return p50, p95


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _skip(reason: str) -> int:
    print("SKIP: CPU latency harness did not run.")
    print(f"reason: {reason}")
    print("latency: not_measured")
    print("accuracy: not_reported")
    print("exit_0_means: skipped_or_measured_latency_only")
    print("No weights were downloaded.")
    return 0


def main() -> int:
    from ai.registry.models import load_registry

    try:
        registry = load_registry()
        card = registry.default()
    except (OSError, ValueError, KeyError) as exc:
        print(f"model registry is invalid: {exc}", file=sys.stderr)
        print("latency: not_measured")
        return 1

    print("ILKA detection latency harness [PROVISIONAL]")
    print(f"registry_model_id={card.model_id} weights_policy={card.weights_policy}")
    weights = resolve_weights_file()
    reason = skip_reason(
        torch_available=_module_available("torch"),
        torchvision_available=_module_available("torchvision"),
        numpy_available=_module_available("numpy"),
        weights_file=weights,
    )
    if reason is not None:
        return _skip(reason)

    assert weights is not None
    import numpy as np

    from cv.detectors.person_cpu import CpuPersonDetector
    from cv.errors import DetectorDependencyError, DetectorInferenceError, DetectorModelError
    from cv.frame import Frame

    try:
        detector = CpuPersonDetector(weights_path=weights)
    except (DetectorDependencyError, DetectorModelError) as exc:
        return _skip(str(exc))

    if detector.model_id != card.cv_model_id:
        print(
            f"warning: detector model_id {detector.model_id} "
            f"does not match registry cv_model_id {card.cv_model_id}"
        )

    image = np.zeros((320, 320, 3), dtype=np.uint8)
    now = datetime.now(UTC)
    samples: list[float] = []
    warmup_observations: int | None = None
    try:
        for index in range(DEFAULT_WARMUP + DEFAULT_FRAMES):
            frame = Frame(
                data=image,
                index=index,
                captured_at=now,
                processed_at=now,
                source_id="bench-synthetic",
            )
            started = time.perf_counter()
            observations = detector.detect(frame)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            if index < DEFAULT_WARMUP:
                warmup_observations = len(observations)
                continue
            samples.append(elapsed_ms)
        p50, p95 = summarize_latency_ms(samples)
    except (DetectorDependencyError, DetectorInferenceError, DetectorModelError, ValueError) as exc:
        print(f"latency measurement failed: {exc}", file=sys.stderr)
        print("latency: not_measured")
        print("accuracy: not_reported")
        return 1

    print("frame_label=[MOCK / SYNTHETIC]")
    print(f"model_id={detector.model_id} model_version={detector.model_version}")
    print("device=cpu")
    print(f"warmup_frames={DEFAULT_WARMUP} timed_frames={len(samples)}")
    print(f"p50_ms={p50:.3f} p95_ms={p95:.3f}")
    print(f"warmup_observation_count={warmup_observations}")
    print("observation_count_is_not_accuracy=true")
    print("accuracy: not_reported")
    print("CUDA was not selected.")
    print("exit_0_means: skipped_or_measured_latency_only")
    print("No weights were downloaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
