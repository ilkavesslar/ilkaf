"""Named person-detector factories. Selection only; no weights are downloaded here."""

from __future__ import annotations

import importlib.util
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cv.detectors.base import PersonDetector
from cv.detectors.person_cpu import MODEL_ID as SSDLITE_MODEL_ID
from cv.detectors.person_cpu import WEIGHTS_ENV as SSDLITE_WEIGHTS_ENV
from cv.detectors.person_cpu import CpuPersonDetector
from cv.detectors.yolo_optional import MODEL_ID as YOLO_MODEL_ID
from cv.detectors.yolo_optional import WEIGHTS_ENV as YOLO_WEIGHTS_ENV
from cv.detectors.yolo_optional import YoloPersonDetector

DEFAULT_DETECTOR = "torchvision-ssdlite"
YOLO_DETECTOR = "yolo"

DetectorFactory = Callable[..., PersonDetector]


@dataclass(frozen=True, slots=True)
class DetectorAvailability:
    name: str
    model_id: str
    available: bool
    reason: str
    default: bool


@dataclass(frozen=True, slots=True)
class _Entry:
    name: str
    model_id: str
    factory: DetectorFactory
    check: Callable[[], str | None]


def _module_missing(*modules: str) -> str | None:
    missing = [name for name in modules if importlib.util.find_spec(name) is None]
    if missing:
        return f"missing runtime: {', '.join(missing)}"
    return None


def _weights_missing(env_name: str) -> str | None:
    value = os.environ.get(env_name, "").strip()
    if not value:
        return f"{env_name} is not set"
    if not Path(value).is_file():
        return f"{env_name} does not point to a file"
    return None


def _ssdlite_check() -> str | None:
    return _module_missing("torch", "torchvision") or _weights_missing(SSDLITE_WEIGHTS_ENV)


def _yolo_check() -> str | None:
    return _module_missing("ultralytics") or _weights_missing(YOLO_WEIGHTS_ENV)


class DetectorRegistry:
    """Lists detectors and builds one by name. Unknown names raise ``KeyError``."""

    def __init__(self, *, default: str = DEFAULT_DETECTOR) -> None:
        self._entries: dict[str, _Entry] = {}
        self._default = default

    def register(
        self,
        name: str,
        *,
        model_id: str,
        factory: DetectorFactory,
        check: Callable[[], str | None] | None = None,
    ) -> None:
        key = name.strip().lower()
        if not key:
            raise ValueError("detector name is required")
        if key in self._entries:
            raise ValueError(f"detector already registered: {key}")
        self._entries[key] = _Entry(key, model_id, factory, check or (lambda: None))

    @property
    def default(self) -> str:
        return self._default

    def names(self) -> list[str]:
        return sorted(self._entries)

    def availability(self) -> list[DetectorAvailability]:
        """Report whether each detector can be built now. Does not load models."""

        rows: list[DetectorAvailability] = []
        for name in self.names():
            entry = self._entries[name]
            reason = entry.check()
            rows.append(
                DetectorAvailability(
                    name=name,
                    model_id=entry.model_id,
                    available=reason is None,
                    reason=reason or "ready",
                    default=name == self._default,
                )
            )
        return rows

    def create(self, name: str | None = None, **kwargs: Any) -> PersonDetector:
        key = (name or self._default).strip().lower()
        entry = self._entries.get(key)
        if entry is None:
            raise KeyError(f"unknown detector {key!r}; choose one of {self.names()}")
        return entry.factory(**kwargs)


def default_registry() -> DetectorRegistry:
    registry = DetectorRegistry()
    registry.register(
        DEFAULT_DETECTOR,
        model_id=SSDLITE_MODEL_ID,
        factory=CpuPersonDetector,
        check=_ssdlite_check,
    )
    registry.register(
        YOLO_DETECTOR,
        model_id=YOLO_MODEL_ID,
        factory=YoloPersonDetector,
        check=_yolo_check,
    )
    return registry


def select_detector(name: str | None = None, **kwargs: Any) -> PersonDetector:
    """Build a detector from the default registry. Missing deps fail closed."""

    return default_registry().create(name, **kwargs)
