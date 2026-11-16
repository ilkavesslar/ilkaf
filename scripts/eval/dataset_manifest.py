#!/usr/bin/env python3
"""Validate ``datasets/MANIFEST.yaml``. Does not download datasets."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.registry.models import parse_simple_yaml

MANIFEST_PATH = ROOT / "datasets" / "MANIFEST.yaml"
LICENSE_STATUS = frozenset({"public_research", "restricted", "unknown"})
COMMERCIAL_USE = frozenset({"yes", "no", "unclear"})
ILKA_USAGE = frozenset({"allowed_for_eval", "requires_review", "do_not_download_here"})
REQUIRED = (
    "id",
    "task",
    "license_status",
    "commercial_use",
    "url",
    "notes",
    "ilka_usage",
)


def validate_manifest(document: Any) -> list[dict[str, str]]:
    """Return the entries or raise ``ValueError`` with the first broken rule."""

    if not isinstance(document, dict):
        raise ValueError("manifest root must be a mapping")
    if document.get("schema_version") != 1:
        raise ValueError("manifest schema_version must be 1")
    if document.get("downloaded") is not False:
        raise ValueError("manifest downloaded must be false; this repo does not vendor datasets")
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest entries must be a non-empty list")
    seen: set[str] = set()
    checked: list[dict[str, str]] = []
    for index, raw in enumerate(entries):
        if not isinstance(raw, dict):
            raise ValueError(f"entry {index} must be a mapping")
        missing = [key for key in REQUIRED if key not in raw]
        if missing:
            raise ValueError(f"entry {index} missing {missing}")
        row = {key: raw[key] for key in REQUIRED}
        for key, value in row.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"entry {index} field {key} must be a non-empty string")
            row[key] = value.strip()
        if row["id"] in seen:
            raise ValueError(f"duplicate dataset id: {row['id']}")
        seen.add(row["id"])
        if row["license_status"] not in LICENSE_STATUS:
            raise ValueError(f"{row['id']}: unknown license_status")
        if row["commercial_use"] not in COMMERCIAL_USE:
            raise ValueError(f"{row['id']}: unknown commercial_use")
        if row["ilka_usage"] not in ILKA_USAGE:
            raise ValueError(f"{row['id']}: unknown ilka_usage")
        if row["commercial_use"] == "no" and row["ilka_usage"] == "allowed_for_eval":
            raise ValueError(f"{row['id']}: commercial_use no cannot be allowed_for_eval")
        if not (row["url"].startswith("https://") or row["url"].startswith("http://")):
            raise ValueError(f"{row['id']}: url must be http(s)")
        checked.append(row)
    return checked


def main() -> int:
    try:
        document = parse_simple_yaml(MANIFEST_PATH.read_text(encoding="utf-8"))
        entries = validate_manifest(document)
    except (OSError, ValueError) as exc:
        print(f"dataset manifest is invalid: {exc}", file=sys.stderr)
        return 1
    print("ILKA dataset manifest")
    print("downloaded=false")
    for row in entries:
        print(
            f"{row['id']} task={row['task']} license_status={row['license_status']} "
            f"commercial_use={row['commercial_use']} ilka_usage={row['ilka_usage']}"
        )
    print("No datasets were downloaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
