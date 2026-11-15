"""Check ILKA_POSTGRES_URL is set. Never print the value."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"


def main() -> int:
    print("FILE_EXISTS", ENV_PATH.is_file())
    found = nonempty = looks_pg = is_sqlite = False
    if ENV_PATH.is_file():
        for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            if key.strip() != "ILKA_POSTGRES_URL":
                continue
            found = True
            value = val.strip().strip('"').strip("'")
            nonempty = bool(value)
            low = value.lower()
            looks_pg = low.startswith("postgres")
            is_sqlite = "sqlite" in low
    ok = found and nonempty and looks_pg and not is_sqlite
    print("KEY_PRESENT", found)
    print("NONEMPTY", nonempty)
    print("LOOKS_POSTGRESQL", looks_pg)
    print("LOOKS_SQLITE", is_sqlite)
    print("PostgreSQL URL configured:", "YES" if ok else "NO")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
