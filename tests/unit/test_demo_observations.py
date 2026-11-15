from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.core.db import get_db_session
from app.main import app
from app.models import AuditLog
from app.schemas.demo_observations import (
    DemoBoundingBox,
    DemoObservation,
    DemoObservationsResponse,
    empty_demo_snapshot,
)
from app.services.demo_observations import (
    DemoRunError,
    load_snapshot,
    observation_from_frame,
    save_snapshot,
)
from cv.frame import MOCK_SYNTHETIC_LABEL, Frame
from cv.observation import BoundingBox, Observation
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import func, select
from tests.helpers.identity import IdentityWorld
from tests.helpers.auth import session_cookie_header


def _auth(world: IdentityWorld, key: str) -> dict[str, str]:
    return session_cookie_header(world.sessions[key])


def _use_store(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setenv("ILKA_DEMO_OBSERVATIONS_PATH", str(path))
    get_settings.cache_clear()


def _observation(**overrides: object) -> DemoObservation:
    payload: dict[str, object] = {
        "observation_id": uuid4(),
        "object_class": "person",
        "confidence": 0.5,
        "bounding_box": {"x_min": 0.1, "y_min": 0.2, "x_max": 0.4, "y_max": 0.8},
        "source_id": "people-detection (1).mp4",
        "model_id": "torchvision-ssdlite320-mobilenet-v3-large",
        "model_version": "0.20.1+cpu",
        "observed_at": datetime(2026, 10, 18, tzinfo=UTC),
        "media_timestamp": datetime(2026, 10, 18, 0, 0, 1, tzinfo=UTC),
        "frame_index": 1,
        "is_synthetic": True,
        "mock_label": MOCK_SYNTHETIC_LABEL,
    }
    payload.update(overrides)
    return DemoObservation.model_validate(payload)


def _frame() -> Frame:
    return Frame(
        data=b"unused",
        index=1,
        captured_at=datetime(2026, 10, 18, tzinfo=UTC),
        processed_at=datetime(2026, 10, 18, tzinfo=UTC),
        source_id="people-detection (1).mp4",
        is_synthetic=True,
        source_kind="file",
        mock_label=MOCK_SYNTHETIC_LABEL,
    )


def _cv_observation(**overrides: object) -> Observation:
    payload: dict[str, object] = {
        "observation_id": uuid4(),
        "source_id": "people-detection (1).mp4",
        "object_class": "person",
        "confidence": 0.42,
        "bounding_box": BoundingBox(x_min=0.1, y_min=0.2, x_max=0.3, y_max=0.6),
        "model_id": "torchvision-ssdlite320-mobilenet-v3-large",
        "model_version": "0.20.1+cpu",
        "observed_at": datetime(2026, 10, 18, tzinfo=UTC),
        "media_timestamp": datetime(2026, 10, 18, tzinfo=UTC),
        "is_synthetic": True,
        "mock_label": MOCK_SYNTHETIC_LABEL,
    }
    payload.update(overrides)
    return Observation(**payload)  # type: ignore[arg-type]


def test_schema_rejects_invalid_confidence_and_boxes() -> None:
    with pytest.raises(ValidationError):
        _observation(confidence=1.2)
    with pytest.raises(ValidationError):
        _observation(confidence=float("nan"))
    with pytest.raises(ValidationError):
        DemoBoundingBox(x_min=0.4, y_min=0.2, x_max=0.4, y_max=0.5)
    with pytest.raises(ValidationError):
        DemoBoundingBox(x_min=-0.1, y_min=0.0, x_max=0.2, y_max=0.2)
    with pytest.raises(ValidationError):
        _observation(is_synthetic=False)
    with pytest.raises(ValidationError):
        _observation(mock_label="real camera")
    with pytest.raises(ValidationError):
        _observation(object_class="forklift")


def test_frame_observation_keeps_synthetic_metadata() -> None:
    parsed = observation_from_frame(_frame(), _cv_observation())
    assert parsed.object_class == "person"
    assert parsed.is_synthetic is True
    assert parsed.mock_label == "[MOCK / SYNTHETIC]"
    assert parsed.source_id == "people-detection (1).mp4"
    assert parsed.model_id == "torchvision-ssdlite320-mobilenet-v3-large"
    assert parsed.model_version == "0.20.1+cpu"
    assert 0.0 <= parsed.confidence <= 1.0
    assert parsed.bounding_box.x_max > parsed.bounding_box.x_min


def test_non_person_observation_is_rejected() -> None:
    with pytest.raises(DemoRunError, match="invalid_observation"):
        observation_from_frame(_frame(), _cv_observation(object_class="vehicle"))


def test_store_bounds_and_empty_state(tmp_path: Path) -> None:
    assert empty_demo_snapshot().demo_status == "empty"
    assert load_snapshot(tmp_path / "missing.json").demo_status == "empty"
    observations = [_observation(observation_id=uuid4()) for _ in range(201)]
    with pytest.raises(ValidationError):
        DemoObservationsResponse(
            demo_status="ready",
            source_status="local_mp4_demo",
            source_id="people-detection (1).mp4",
            frames_processed=30,
            model_id="torchvision-ssdlite320-mobilenet-v3-large",
            model_version="0.20.1+cpu",
            observations=observations,
        )
    kept = observations[:200]
    snapshot = DemoObservationsResponse(
        demo_status="ready",
        source_status="local_mp4_demo",
        source_id="people-detection (1).mp4",
        frames_processed=30,
        model_id="torchvision-ssdlite320-mobilenet-v3-large",
        model_version="0.20.1+cpu",
        observations=kept,
    )
    target = tmp_path / "demo.json"
    save_snapshot(snapshot, target)
    loaded = load_snapshot(target)
    assert len(loaded.observations) == 200
    assert loaded.mock_label == "[MOCK / SYNTHETIC]"
    assert "incident" not in loaded.model_dump()


async def _audit_count() -> int:
    generator = app.dependency_overrides[get_db_session]()
    session = await generator.__anext__()
    try:
        count = await session.scalar(select(func.count()).select_from(AuditLog))
        return int(count or 0)
    finally:
        await generator.aclose()


@pytest.mark.asyncio
async def test_demo_api_auth_empty_state_and_no_incidents(
    auth_env: tuple[AsyncClient, IdentityWorld],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, world = auth_env
    _use_store(monkeypatch, tmp_path / "demo.json")

    missing = await client.get("/api/v1/demo/person-observations")
    assert missing.status_code == 401

    denied = await client.get(
        "/api/v1/demo/person-observations",
        headers=_auth(world, "VIEWER"),
    )
    assert denied.status_code == 403

    empty = await client.get(
        "/api/demo/person-observations",
        headers=_auth(world, "OPERATOR"),
    )
    assert empty.status_code == 200
    body = empty.json()
    assert body["demo_status"] == "empty"
    assert body["mock_label"] == "[MOCK / SYNTHETIC]"
    assert body["observations"] == []
    assert body["record_kind"] == "person_observation_demo"
    assert "incident" not in body

    blocked_run = await client.post(
        "/api/v1/demo/person-observations/runs",
        headers=_auth(world, "OPERATOR"),
        json={"max_frames": 30},
    )
    assert blocked_run.status_code == 403

    def _fake(
        _path: object,
        *,
        max_frames: int = 30,
        **_kwargs: object,
    ) -> DemoObservationsResponse:
        assert max_frames == 30
        snapshot = DemoObservationsResponse(
            demo_status="ready",
            source_status="local_mp4_demo",
            source_id="people-detection (1).mp4",
            frames_processed=30,
            model_id="torchvision-ssdlite320-mobilenet-v3-large",
            model_version="0.20.1+cpu",
            observations=[_observation()],
        )
        save_snapshot(snapshot)
        return snapshot

    monkeypatch.setattr("app.api.demo_observations.execute_demo_run", _fake)
    created = await client.post(
        "/api/v1/demo/person-observations/runs",
        headers=_auth(world, "SAFETY_OFFICER"),
        json={},
    )
    assert created.status_code == 200
    assert created.json()["observations"][0]["object_class"] == "person"
    assert created.json()["observations"][0]["is_synthetic"] is True
    listed = await client.get(
        "/api/v1/demo/person-observations",
        headers=_auth(world, "OPERATOR"),
    )
    assert listed.status_code == 200
    assert listed.json()["frames_processed"] == 30
    assert await _audit_count() == 0
