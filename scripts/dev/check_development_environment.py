#!/usr/bin/env python3
"""Pre-flight readiness check for local ILKA development.

Reports only. Does not install packages, start/stop services, modify the
database, or print secret values.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
BACKEND_VENV = ROOT / ".venv" / "bin" / "python"
CV_VENV = ROOT / ".venv-cv" / "bin" / "python"
WEIGHTS_DEFAULT = ROOT / "data" / "models" / "ssdlite320_mobilenet_v3_large_coco.pth"
WEIGHTS_ENV = "ILKA_CV_PERSON_WEIGHTS"
DB_KEYS = ("DATABASE_URL", "ILKA_POSTGRES_URL")
REQUIRED_ENV_KEYS = ("AUTH_SECRET_KEY",)


def _line(status: str, message: str) -> None:
    print(f"[{status}] {message}")


def _load_dotenv_keys(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def _has_nonempty(values: dict[str, str], key: str) -> bool:
    return bool(values.get(key, "").strip())


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, f"{type(exc).__name__}"
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def main() -> int:
    print("ILKA DEVELOPMENT ENVIRONMENT")
    print()
    fails = 0
    warns = 0
    env_values = _load_dotenv_keys(ENV_PATH)

    if BACKEND_VENV.is_file():
        code, out = _run(
            [
                str(BACKEND_VENV),
                "-c",
                "import sys; import fastapi; print(sys.version.split()[0])",
            ]
        )
        if code == 0:
            _line("PASS", f"Backend Python environment (.venv, Python {out.splitlines()[-1]})")
        else:
            _line("FAIL", "Backend Python environment present but FastAPI import failed")
            fails += 1
    else:
        _line("FAIL", "Backend Python environment missing (.venv)")
        fails += 1

    if ENV_PATH.is_file():
        _line("PASS", "Environment configuration found (.env)")
    else:
        _line("FAIL", "Environment configuration missing (.env); copy from .env.example")
        fails += 1

    if any(_has_nonempty(env_values, key) for key in DB_KEYS):
        _line("PASS", "Database configuration present")
    else:
        _line("FAIL", "Database configuration missing (set DATABASE_URL or ILKA_POSTGRES_URL)")
        fails += 1

    missing_required = [k for k in REQUIRED_ENV_KEYS if not _has_nonempty(env_values, k)]
    if missing_required:
        _line("WARN", f"Recommended auth config incomplete ({', '.join(missing_required)})")
        warns += 1
    else:
        _line("PASS", "Authentication secret present (value not shown)")

    if CV_VENV.is_file():
        _line("PASS", "CV environment (.venv-cv)")
        code, out = _run(
            [
                str(CV_VENV),
                "-c",
                (
                    "import torch, torchvision; "
                    "from torchvision.ops import nms; "
                    "print(torch.__version__, torchvision.__version__, "
                    "torch.cuda.is_available())"
                ),
            ]
        )
        if code == 0:
            parts = out.splitlines()[-1].split()
            torch_v, tv_v, cuda = parts[0], parts[1], parts[2]
            if cuda.lower() in {"false", "0"}:
                _line("PASS", f"PyTorch and TorchVision ({torch_v} / {tv_v}, CPU)")
            else:
                _line("WARN", f"PyTorch and TorchVision ({torch_v} / {tv_v}, CUDA={cuda})")
                warns += 1
        else:
            _line("FAIL", "PyTorch and TorchVision import/NMS check failed in .venv-cv")
            fails += 1
    else:
        _line("FAIL", "CV environment missing (.venv-cv)")
        fails += 1

    weights = env_values.get(WEIGHTS_ENV, "").strip() or os.environ.get(WEIGHTS_ENV, "").strip()
    weights_path = Path(weights) if weights else WEIGHTS_DEFAULT
    if weights_path.is_file():
        _line("PASS", f"Person detector weights present ({weights_path.name})")
    else:
        _line(
            "WARN",
            "Person detector weights not found "
            f"(set {WEIGHTS_ENV} or fetch into data/models/)",
        )
        warns += 1

    node = shutil.which("node")
    npm = shutil.which("npm")
    frontend_modules = ROOT / "frontend" / "node_modules"
    if node and npm and frontend_modules.is_dir():
        node_v = _run([node, "--version"])[1]
        _line("PASS", f"Node/npm ({node_v}, frontend/node_modules present)")
    elif node and npm:
        _line("WARN", "Node/npm available but frontend/node_modules missing")
        warns += 1
    else:
        _line("FAIL", "Node/npm not available on PATH")
        fails += 1

    if (ROOT / ".git").is_dir():
        _line("PASS", "Git repository metadata present (.git)")
    else:
        _line("WARN", "Git repository metadata missing (.git); reconnect to remote before push")
        warns += 1

    print()
    if fails:
        print("RESULT: DEVELOPMENT ENVIRONMENT NOT READY")
        return 1
    if warns:
        print("RESULT: DEVELOPMENT ENVIRONMENT READY WITH WARNINGS")
        return 0
    print("RESULT: DEVELOPMENT ENVIRONMENT READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
