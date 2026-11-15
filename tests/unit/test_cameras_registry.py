import pytest
from httpx import AsyncClient
from uuid import uuid4

from tests.helpers.auth import session_cookie_header
from tests.helpers.identity import IdentityWorld


def _auth(world: IdentityWorld, key: str) -> dict[str, str]:
    return session_cookie_header(world.sessions[key])


@pytest.mark.asyncio
async def test_camera_registry_site_scope(
    auth_env: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env
    payload = {
        "name": "Gate Cam",
        "code": "GATE-1",
        "description": "metadata only",
        "location": "north gate",
        "status": "ACTIVE",
    }
    created = await client.post(
        f"/api/v1/sites/{world.site_a.id}/cameras",
        headers=_auth(world, "SITE_MANAGER"),
        json=payload,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["code"] == "GATE-1"
    assert "rtsp" not in body
    camera_id = body["id"]

    listed = await client.get(
        f"/api/sites/{world.site_a.id}/cameras",
        headers=_auth(world, "VIEWER"),
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    denied_site = await client.get(
        f"/api/v1/sites/{world.site_b.id}/cameras",
        headers=_auth(world, "VIEWER"),
    )
    assert denied_site.status_code == 404

    denied_create = await client.post(
        f"/api/v1/sites/{world.site_a.id}/cameras",
        headers=_auth(world, "VIEWER"),
        json={**payload, "code": "GATE-2"},
    )
    assert denied_create.status_code == 403

    fetched = await client.get(f"/api/v1/cameras/{camera_id}", headers=_auth(world, "OPERATOR"))
    assert fetched.status_code == 200

    patched = await client.patch(
        f"/api/cameras/{camera_id}",
        headers=_auth(world, "SITE_MANAGER"),
        json={"status": "MAINTENANCE"},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "MAINTENANCE"

    viewer_patch = await client.patch(
        f"/api/v1/cameras/{camera_id}",
        headers=_auth(world, "VIEWER"),
        json={"status": "INACTIVE"},
    )
    assert viewer_patch.status_code == 403


@pytest.mark.asyncio
async def test_org_admin_foreign_camera_is_404(
    auth_env: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env
    created = await client.post(
        f"/api/v1/sites/{world.other_site.id}/cameras",
        headers=_auth(world, "SYSTEM_ADMIN"),
        json={"name": "Foreign Cam", "code": "FOR-1", "status": "ACTIVE"},
    )
    assert created.status_code == 201
    camera_id = created.json()["id"]

    missing = await client.get(f"/api/v1/cameras/{uuid4()}", headers=_auth(world, "ORG_ADMIN"))
    assert missing.status_code == 404
    foreign = await client.get(
        f"/api/v1/cameras/{camera_id}", headers=_auth(world, "ORG_ADMIN")
    )
    assert foreign.status_code == 404
    assert foreign.json()["error"]["message"] == missing.json()["error"]["message"]
    listed = await client.get(
        f"/api/v1/sites/{world.other_site.id}/cameras",
        headers=_auth(world, "ORG_ADMIN"),
    )
    assert listed.status_code == 404
    allowed = await client.get(
        f"/api/v1/cameras/{camera_id}", headers=_auth(world, "SYSTEM_ADMIN")
    )
    assert allowed.status_code == 200
    viewer_home = await client.get(
        f"/api/v1/sites/{world.site_b.id}/cameras", headers=_auth(world, "VIEWER")
    )
    assert viewer_home.status_code == 404
