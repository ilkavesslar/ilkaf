"""Run Alembic without printing connection strings.

Loads URLs through Alembic env.py → Settings (repo-root .env via pydantic-settings).
Do not import python-dotenv.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def redact(text: str) -> str:
    text = re.sub(r"postgres(?:ql)?(?:\+asyncpg)?://\S+", "postgresql://***", text, flags=re.I)
    text = re.sub(r"[\w.-]*neon\.tech\S*", "***/neon.host", text, flags=re.I)
    return text


def main() -> int:
    env = os.environ.copy()
    env.setdefault("ENVIRONMENT", "development")
    args = sys.argv[1:] or ["current"]
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
    )
    sys.stdout.write(redact(result.stdout))
    sys.stderr.write(redact(result.stderr))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
