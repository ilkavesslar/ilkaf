from __future__ import annotations

import pytest
from app.core.config import get_settings
from httpx import AsyncClient
from tests.helpers.identity import IdentityWorld
from tests.helpers.auth import session_cookie_header


def _auth(world: IdentityWorld, key: str) -> dict[str, str]:
    return session_cookie_header(world.sessions[key])


def _enable(monkeypatch: pytest.MonkeyPatch, world: IdentityWorld, *, site: str) -> None:
    monkeypatch.setenv("ILKA_LAB_CAMERAS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("ILKA_LAB_CAMERA_ORGANIZATION_ID", str(world.org.id))
    monkeypatch.setenv("ILKA_LAB_CAMERA_SITE_ID", site)
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_lab_cameras_require_auth_and_site_scope(
    auth_env: tuple[AsyncClient, IdentityWorld],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, world = auth_env
    _enable(monkeypatch, world, site=str(world.site_a.id))

    missing = await client.get("/api/v1/lab/cameras")
    assert missing.status_code == 401

    allowed = await client.get("/api/v1/lab/cameras", headers=_auth(world, "VIEWER"))
    assert allowed.status_code == 200
    body = allowed.json()
    assert [item["camera_id"] for item in body["cameras"]] == [
        "vigi-c320i-192.168.1.17",
        "vigi-c320i-192.168.1.18",
    ]
    assert "password" not in allowed.text
    assert "rtsp://" not in allowed.text

    _enable(monkeypatch, world, site=str(world.site_b.id))
    denied = await client.get("/api/v1/lab/cameras", headers=_auth(world, "VIEWER"))
    assert denied.status_code == 403

    monkeypatch.setenv("ILKA_LAB_CAMERA_ORGANIZATION_ID", str(world.other_org.id))
    monkeypatch.setenv("ILKA_LAB_CAMERA_SITE_ID", str(world.other_site.id))
    get_settings.cache_clear()
    cross_org = await client.get("/api/v1/lab/cameras", headers=_auth(world, "OPERATOR"))
    assert cross_org.status_code == 403

    admin = "SYSTEM_ADMIN" if "SYSTEM_ADMIN" in world.users else "ORG_ADMIN"
    unknown = await client.get(
        "/api/v1/lab/cameras/not-a-camera/mjpeg",
        headers=_auth(world, admin),
    )
    assert unknown.status_code == 404


@pytest.mark.asyncio
async def test_lab_cameras_hidden_when_disabled_or_production(
    auth_env: tuple[AsyncClient, IdentityWorld],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, world = auth_env
    monkeypatch.setenv("ILKA_LAB_CAMERAS_ENABLED", "false")
    get_settings.cache_clear()
    hidden = await client.get("/api/v1/lab/cameras", headers=_auth(world, "ORG_ADMIN"))
    assert hidden.status_code == 404

    monkeypatch.setenv("ILKA_LAB_CAMERAS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()
    production = await client.get("/api/v1/lab/cameras", headers=_auth(world, "ORG_ADMIN"))
    assert production.status_code == 404


@pytest.mark.asyncio
async def test_stream_refuses_missing_account(
    auth_env: tuple[AsyncClient, IdentityWorld],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, world = auth_env
    _enable(monkeypatch, world, site=str(world.site_a.id))
    monkeypatch.delenv("ILKA_CAMERA_PASSWORD", raising=False)
    response = await client.get(
        "/api/v1/lab/cameras/vigi-c320i-192.168.1.17/mjpeg",
        headers=_auth(world, "VIEWER"),
    )
    assert response.status_code == 503
    assert "password" not in response.text.lower() or "not configured" in response.text.lower()
