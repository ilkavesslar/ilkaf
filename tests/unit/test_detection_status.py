from __future__ import annotations

import pytest
from app.core.config import get_settings
from app.main import app
from app.services.detection_state import get_detection_state
from tests.helpers.auth import session_cookie_header

from cv.capabilities import clear_capability_cache, refresh_capabilities


def test_detection_routes_are_registered() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/detection/capabilities" in paths
    assert "/api/v1/detection/observations" in paths


async def test_detection_status_requires_a_session(auth_env) -> None:
    client, _world = auth_env
    capabilities = await client.get("/api/v1/detection/capabilities")
    observations = await client.get("/api/v1/detection/observations")
    assert capabilities.status_code == 401
    assert observations.status_code == 401


async def test_capability_request_does_not_probe(auth_env, monkeypatch: pytest.MonkeyPatch) -> None:
    clear_capability_cache()
    calls = {"count": 0}

    def probed():
        calls["count"] += 1
        from cv.capabilities import DetectionCapability

        return DetectionCapability(
            "person",
            "Person detection",
            "available",
            "The CPU person detector is installed. Live camera inference is not connected.",
        )

    monkeypatch.setattr("cv.capabilities.probe_person", probed)
    client, world = auth_env
    headers = session_cookie_header(world.sessions["VIEWER"])
    first = await client.get("/api/v1/detection/capabilities", headers=headers)
    assert first.status_code == 200
    assert calls["count"] == 0
    body = first.json()
    by_id = {item["capability_id"]: item for item in body["capabilities"]}
    assert set(by_id) == {"person", "ppe", "fall", "fire_smoke"}
    assert by_id["person"]["status"] == "not_configured"
    assert "has not been checked" in by_id["person"]["detail"]
    for capability_id in ("ppe", "fall", "fire_smoke"):
        assert by_id[capability_id]["status"] == "not_implemented"
    assert ".pth" not in first.text.lower()
    refresh_capabilities()
    assert calls["count"] == 1
    second = await client.get("/api/v1/detection/capabilities", headers=headers)
    assert second.json()["capabilities"][0]["status"] == "available"
    assert calls["count"] == 1
    clear_capability_cache()


async def test_live_observations_require_a_visible_camera(auth_env, monkeypatch: pytest.MonkeyPatch) -> None:
    client, world = auth_env
    headers = session_cookie_header(world.sessions["VIEWER"])
    admin = session_cookie_header(world.sessions["SYSTEM_ADMIN"])
    missing = await client.get("/api/v1/detection/observations", headers=headers)
    assert missing.status_code == 400
    hidden = await client.get(
        "/api/v1/detection/observations",
        headers=headers,
        params={"camera_id": "vigi-c320i-192.168.1.17"},
    )
    assert hidden.status_code == 404

    monkeypatch.setenv("ILKA_LAB_CAMERAS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("ILKA_LAB_CAMERA_ORGANIZATION_ID", str(world.org.id))
    monkeypatch.setenv("ILKA_LAB_CAMERA_SITE_ID", str(world.site_a.id))
    get_settings.cache_clear()
    allowed = await client.get(
        "/api/v1/detection/observations",
        headers=headers,
        params={"camera_id": "vigi-c320i-192.168.1.17"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["status"] == "not_connected"
    assert allowed.json()["items"] == []
    assert "rtsp://" not in allowed.text.lower()

    monkeypatch.setenv("ILKA_LAB_CAMERA_SITE_ID", str(world.site_b.id))
    get_settings.cache_clear()
    denied = await client.get(
        "/api/v1/detection/observations",
        headers=headers,
        params={"camera_id": "vigi-c320i-192.168.1.17"},
    )
    assert denied.status_code == 403

    created = await client.post(
        f"/api/v1/sites/{world.site_b.id}/cameras",
        headers=admin,
        json={"name": "Gate", "code": "GATE1"},
    )
    assert created.status_code == 201
    camera_id = created.json()["id"]
    outsider = await client.get(
        "/api/v1/detection/observations",
        headers=headers,
        params={"camera_id": camera_id},
    )
    assert outsider.status_code == 404
    owner = await client.get(
        "/api/v1/detection/observations",
        headers=admin,
        params={"camera_id": camera_id},
    )
    assert owner.status_code == 200
    assert owner.json()["status"] == "not_connected"
    get_detection_state().clear()
    get_settings.cache_clear()
