"""Bounded lab cache for one local-MP4 person-detection run.

The cache is a JSON file so the API process and a separate runner share it.
It is not a database, not durable product storage, and not an incident log.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.demo_observations import (
    DemoObservation,
    DemoObservationsResponse,
    empty_demo_snapshot,
)

_MOCK_SYNTHETIC_LABEL = "[MOCK / SYNTHETIC]"

_MAX_FRAMES = 30
_MAX_OBSERVATIONS = 200
_VIDEO_NAME = "people-detection (1).mp4"


class DemoRunError(Exception):
    """Stable failure code. HTTP layers map this to a fixed message."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def demo_video_path() -> Path:
    return repo_root() / "data" / "videos" / _VIDEO_NAME


def demo_weights_path() -> Path:
    configured = os.environ.get("ILKA_CV_PERSON_WEIGHTS", "").strip()
    if configured:
        return Path(configured)
    return repo_root() / "data" / "models" / "ssdlite320_mobilenet_v3_large_coco.pth"


def store_path() -> Path:
    configured = get_settings().demo_observations_path.strip()
    if configured:
        return Path(configured)
    return repo_root() / "data" / "cache" / "demo-person-observations.json"


def _bounded_frames(max_frames: int) -> int:
    if isinstance(max_frames, bool) or not isinstance(max_frames, int):
        raise DemoRunError("invalid_frame_count")
    if max_frames < 1 or max_frames > _MAX_FRAMES:
        raise DemoRunError("invalid_frame_count")
    return max_frames


def _ensure_repo_on_path() -> None:
    root = str(repo_root())
    if root not in sys.path:
        sys.path.insert(0, root)


def observation_from_frame(frame: Any, item: Any) -> DemoObservation:
    if frame.source_kind != "file":
        raise DemoRunError("invalid_observation")
    if item.source_id != frame.source_id:
        raise DemoRunError("invalid_observation")
    if not item.model_id or not item.model_version:
        raise DemoRunError("invalid_observation")
    try:
        return DemoObservation(
            observation_id=item.observation_id,
            object_class=item.object_class,
            confidence=item.confidence,
            bounding_box={
                "x_min": item.bounding_box.x_min,
                "y_min": item.bounding_box.y_min,
                "x_max": item.bounding_box.x_max,
                "y_max": item.bounding_box.y_max,
            },
            source_id=item.source_id,
            model_id=item.model_id,
            model_version=item.model_version,
            observed_at=item.observed_at,
            media_timestamp=item.media_timestamp,
            frame_index=frame.index,
            is_synthetic=item.is_synthetic,
            mock_label=item.mock_label,
        )
    except (ValidationError, TypeError) as exc:
        raise DemoRunError("invalid_observation") from exc


def load_snapshot(path: Path | None = None) -> DemoObservationsResponse:
    target = store_path() if path is None else path
    if not target.is_file():
        return empty_demo_snapshot()
    try:
        payload = target.read_text(encoding="utf-8")
        return DemoObservationsResponse.model_validate_json(payload)
    except (OSError, ValidationError, UnicodeError) as exc:
        raise DemoRunError("store_unreadable") from exc


def save_snapshot(snapshot: DemoObservationsResponse, path: Path | None = None) -> None:
    bounded = snapshot.model_copy(
        update={"observations": list(snapshot.observations[:_MAX_OBSERVATIONS])}
    )
    target = store_path() if path is None else path
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(bounded.model_dump_json(), encoding="utf-8")
    temporary.replace(target)


def execute_demo_run(
    path: Path | None = None,
    *,
    max_frames: int = _MAX_FRAMES,
    video_path: Path | None = None,
    weights_path: Path | None = None,
) -> DemoObservationsResponse:
    """Run FileSource and CpuPersonDetector, then replace the lab cache."""

    limit = _bounded_frames(max_frames)
    video = demo_video_path() if video_path is None else video_path
    weights = demo_weights_path() if weights_path is None else weights_path
    if not video.is_file():
        raise DemoRunError("video_missing")
    if not weights.is_file():
        raise DemoRunError("weights_missing")
    _ensure_repo_on_path()
    try:
        from cv.detectors.person_cpu import CpuPersonDetector
        from cv.errors import (
            CvDependencyError,
            DetectorDependencyError,
            DetectorInferenceError,
            DetectorModelError,
            VideoSourceError,
        )
        from cv.streams.file import FileSource
    except ImportError as exc:
        raise DemoRunError("runtime_missing") from exc

    try:
        detector = CpuPersonDetector(weights_path=weights)
    except DetectorModelError as exc:
        raise DemoRunError("weights_rejected") from exc
    except DetectorDependencyError as exc:
        raise DemoRunError("runtime_missing") from exc

    collected: list[DemoObservation] = []
    model_id = detector.model_id
    model_version = detector.model_version
    source_id = video.name
    frames = 0
    try:
        with FileSource(
            video,
            source_id=source_id,
            timeline_origin=datetime(2026, 10, 18, tzinfo=UTC),
        ) as source:
            while frames < limit and len(collected) < _MAX_OBSERVATIONS:
                frame = source.read()
                if frame is None:
                    break
                if not frame.is_synthetic or frame.mock_label != _MOCK_SYNTHETIC_LABEL:
                    raise DemoRunError("invalid_observation")
                for item in detector.detect(frame):
                    if len(collected) >= _MAX_OBSERVATIONS:
                        break
                    collected.append(observation_from_frame(frame, item))
                frames += 1
    except CvDependencyError as exc:
        raise DemoRunError("runtime_missing") from exc
    except VideoSourceError as exc:
        raise DemoRunError("video_unreadable") from exc
    except DetectorInferenceError as exc:
        raise DemoRunError("inference_failed") from exc

    if frames == 0:
        raise DemoRunError("video_unreadable")
    snapshot = DemoObservationsResponse(
        demo_status="ready",
        source_status="local_mp4_demo",
        source_id=source_id,
        source_kind="file",
        is_synthetic=True,
        mock_label=_MOCK_SYNTHETIC_LABEL,
        frames_processed=frames,
        model_id=model_id,
        model_version=model_version,
        observations=collected,
    )
    save_snapshot(snapshot, path)
    return snapshot
