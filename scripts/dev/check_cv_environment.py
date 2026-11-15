#!/usr/bin/env python3
"""Validate the isolated ILKA lab CV environment (Intel Mac / CPU).

Does not touch the database, backend process, frontend, or production config.
Does not download weights. Prints PASS / WARN / FAIL lines and a summary.
"""

from __future__ import annotations

import importlib.util
import os
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WEIGHTS_ENV = "ILKA_CV_PERSON_WEIGHTS"
WEIGHTS_BASENAME = "ssdlite320_mobilenet_v3_large_coco.pth"


def _line(status: str, message: str) -> None:
    print(f"[{status}] {message}")


def main() -> int:
    print("ILKA CV Environment Check")
    print()

    fails = 0
    warns = 0

    py = sys.version_info
    if py.major == 3 and py.minor >= 11:
        _line("PASS", f"Python version {py.major}.{py.minor}.{py.micro}")
    else:
        _line("FAIL", f"Python version {py.major}.{py.minor}.{py.micro} (need 3.11+)")
        fails += 1

    machine = platform.machine()
    system = platform.system()
    if system == "Darwin" and machine in {"x86_64", "i386"}:
        _line("PASS", f"Intel macOS architecture detected ({machine})")
    elif system == "Darwin" and machine in {"arm64", "aarch64"}:
        _line("WARN", f"Apple Silicon detected ({machine}); use arm64 CPU wheels, not the x86_64 pin file")
        warns += 1
    else:
        _line("WARN", f"Non-macOS or unknown arch ({system} {machine})")
        warns += 1

    try:
        import torch
    except Exception as exc:  # noqa: BLE001 — diagnostic surface
        _line("FAIL", f"PyTorch import ({type(exc).__name__}: {exc})")
        fails += 1
        torch = None  # type: ignore[assignment]
    else:
        _line("PASS", f"PyTorch import ({torch.__version__})")

    try:
        import torchvision
    except Exception as exc:  # noqa: BLE001
        _line("FAIL", f"TorchVision import ({type(exc).__name__}: {exc})")
        fails += 1
        torchvision = None  # type: ignore[assignment]
    else:
        _line("PASS", f"TorchVision import ({torchvision.__version__})")

    if torch is not None and torchvision is not None:
        try:
            from torchvision.ops import nms

            boxes = torch.tensor([[0.0, 0.0, 10.0, 10.0], [1.0, 1.0, 11.0, 11.0]])
            scores = torch.tensor([0.9, 0.8])
            out = nms(boxes, scores, 0.5)
            if out.numel() < 1:
                raise RuntimeError("nms returned empty result")
            _line("PASS", "TorchVision NMS operation")
        except Exception as exc:  # noqa: BLE001
            _line("FAIL", f"TorchVision NMS operation ({type(exc).__name__}: {exc})")
            fails += 1

        if torch.cuda.is_available():
            _line("WARN", "CUDA is available; ILKA lab detector is CPU-only by design")
            warns += 1
        else:
            _line("PASS", "CPU execution available (CUDA not required)")

        try:
            _ = torch.zeros(1, device="cpu")
            _line("PASS", "CPU tensor allocation")
        except Exception as exc:  # noqa: BLE001
            _line("FAIL", f"CPU tensor allocation ({type(exc).__name__}: {exc})")
            fails += 1
    else:
        _line("FAIL", "TorchVision NMS operation (blocked by import failure)")
        fails += 1
        _line("FAIL", "CPU execution available (blocked by import failure)")
        fails += 1

    CpuPersonDetector = None  # type: ignore[assignment,misc]
    CV_ENV = WEIGHTS_ENV
    try:
        import cv  # noqa: F401
        from cv.detectors.person_cpu import (
            WEIGHTS_ENV as CV_ENV,
            CpuPersonDetector,
        )

        _line("PASS", "ILKA CV package import")
    except Exception as exc:  # noqa: BLE001
        _line("FAIL", f"ILKA CV package import ({type(exc).__name__}: {exc})")
        fails += 1

    if importlib.util.find_spec("cv2") is None:
        _line("WARN", "OpenCV (cv2) not installed in this interpreter")
        warns += 1
    else:
        import cv2

        _line("PASS", f"OpenCV import ({cv2.__version__})")

    weights_ready = False
    weights_path = os.environ.get(CV_ENV, "").strip()
    if not weights_path:
        default_weights = ROOT / "data" / "models" / WEIGHTS_BASENAME
        if default_weights.is_file():
            weights_path = str(default_weights)
            _line("WARN", f"{CV_ENV} unset; using local {WEIGHTS_BASENAME} for checks only")
            warns += 1
    if not weights_path:
        _line("WARN", f"Person detector weights not configured ({CV_ENV} unset)")
        warns += 1
    else:
        path = Path(weights_path)
        if not path.is_file():
            _line("WARN", f"Person detector weights path missing: {path.name}")
            warns += 1
            weights_ready = False
        else:
            try:
                from cv.detectors.person_cpu import verify_weights_file

                verify_weights_file(path)
                _line("PASS", f"Person detector weights verified ({path.name})")
                weights_ready = True
            except Exception as exc:  # noqa: BLE001
                _line("WARN", f"Person detector weights present but not verified ({exc})")
                warns += 1
                weights_ready = False

    if weights_ready and CpuPersonDetector is not None:
        try:
            detector = CpuPersonDetector(weights_path=weights_path, min_confidence=0.25)
            _line(
                "PASS",
                f"CpuPersonDetector init ({detector.model_id} / {detector.model_version})",
            )
        except Exception as exc:  # noqa: BLE001
            _line("FAIL", f"CpuPersonDetector init ({type(exc).__name__}: {exc})")
            fails += 1

    print()
    if fails:
        print("Result: ENVIRONMENT NOT READY")
        return 1
    if warns and not weights_ready:
        print("Result: ENVIRONMENT READY — MODEL WEIGHTS REQUIRED")
        return 0
    if warns:
        print("Result: ENVIRONMENT READY WITH WARNINGS")
        return 0
    print("Result: ENVIRONMENT READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
