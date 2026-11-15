from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.helpers.auth import session_cookie_header
from tests.helpers.identity import IdentityWorld


def _auth(world: IdentityWorld, key: str) -> dict[str, str]:
    return session_cookie_header(world.sessions[key])


@pytest.mark.asyncio
async def test_me_authenticated(
    auth_env: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env
    response = await client.get("/api/v1/me", headers=_auth(world, "VIEWER"))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "viewer@example.com"
    assert "VIEWER" in body["roles"]
    assert any(site["name"] == "Main Factory" for site in body["sites"])
    assert "access_token" not in body
    alias = await client.get("/api/me", headers=_auth(world, "VIEWER"))
    assert alias.status_code == 200
    assert alias.json()["id"] == body["id"]


@pytest.mark.asyncio
async def test_inactive_user_rejected(
    auth_env: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env
    response = await client.get("/api/v1/me", headers=_auth(world, "INACTIVE"))
    assert response.status_code == 403
    assert "inactive" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_unprovisioned_identity(
    auth_env: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, _world = auth_env
    response = await client.get(
        "/api/v1/me",
        headers=session_cookie_header("not-a-valid-session-token"),
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sites_are_scoped(
    auth_env: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env
    viewer = await client.get("/api/v1/sites", headers=_auth(world, "VIEWER"))
    assert viewer.status_code == 200
    names = {row["name"] for row in viewer.json()}
    assert names == {"Main Factory"}

    admin = await client.get("/api/sites", headers=_auth(world, "ORG_ADMIN"))
    assert admin.status_code == 200
    admin_names = {row["name"] for row in admin.json()}
    assert "Main Factory" in admin_names
    assert "Warehouse" in admin_names
    assert "Other Plant" not in admin_names

    system = await client.get("/api/v1/sites", headers=_auth(world, "SYSTEM_ADMIN"))
    assert system.status_code == 200
    system_names = {row["name"] for row in system.json()}
    assert "Other Plant" in system_names


@pytest.mark.asyncio
async def test_cross_site_access_denied(
    auth_env: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env
    allowed = await client.get(
        f"/api/v1/sites/{world.site_a.id}", headers=_auth(world, "OPERATOR")
    )
    assert allowed.status_code == 200
    denied = await client.get(
        f"/api/v1/sites/{world.site_b.id}", headers=_auth(world, "OPERATOR")
    )
    assert denied.status_code == 404
    other = await client.get(
        f"/api/sites/{world.other_site.id}", headers=_auth(world, "OPERATOR")
    )
    assert other.status_code == 404


@pytest.mark.asyncio
async def test_site_create_permissions(
    auth_env: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env
    payload = {"name": "Packing", "code": "PACK", "description": "line"}
    denied = await client.post("/api/v1/sites", headers=_auth(world, "VIEWER"), json=payload)
    assert denied.status_code == 403
    operator = await client.post("/api/sites", headers=_auth(world, "OPERATOR"), json=payload)
    assert operator.status_code == 403
    manager = await client.post(
        "/api/v1/sites", headers=_auth(world, "SITE_MANAGER"), json=payload
    )
    assert manager.status_code == 403
    created = await client.post("/api/v1/sites", headers=_auth(world, "ORG_ADMIN"), json=payload)
    assert created.status_code == 201
    assert created.json()["code"] == "PACK"
    duplicate = await client.post("/api/v1/sites", headers=_auth(world, "ORG_ADMIN"), json=payload)
    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_site_patch_matrix(
    auth_env: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env
    viewer = await client.patch(
        f"/api/v1/sites/{world.site_a.id}",
        headers=_auth(world, "VIEWER"),
        json={"description": "nope"},
    )
    assert viewer.status_code == 403
    officer = await client.patch(
        f"/api/v1/sites/{world.site_a.id}",
        headers=_auth(world, "SAFETY_OFFICER"),
        json={"description": "nope"},
    )
    assert officer.status_code == 403
    manager = await client.patch(
        f"/api/v1/sites/{world.site_a.id}",
        headers=_auth(world, "SITE_MANAGER"),
        json={"description": "updated by manager"},
    )
    assert manager.status_code == 200
    assert manager.json()["description"] == "updated by manager"
    cross = await client.patch(
        f"/api/v1/sites/{world.site_b.id}",
        headers=_auth(world, "SITE_MANAGER"),
        json={"description": "cross"},
    )
    assert cross.status_code == 404
    missing = await client.get(f"/api/v1/sites/{uuid4()}", headers=_auth(world, "ORG_ADMIN"))
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_org_admin_foreign_site_is_404(
    auth_env: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env
    missing = await client.get(f"/api/v1/sites/{uuid4()}", headers=_auth(world, "ORG_ADMIN"))
    assert missing.status_code == 404
    foreign = await client.get(
        f"/api/v1/sites/{world.other_site.id}", headers=_auth(world, "ORG_ADMIN")
    )
    assert foreign.status_code == 404
    assert foreign.json()["error"]["message"] == missing.json()["error"]["message"]
    allowed = await client.get(
        f"/api/v1/sites/{world.other_site.id}", headers=_auth(world, "SYSTEM_ADMIN")
    )
    assert allowed.status_code == 200
    assert allowed.json()["name"] == "Other Plant"


@pytest.mark.asyncio
async def test_role_read_access(
    auth_env: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env
    for key in ("SITE_MANAGER", "SAFETY_OFFICER", "OPERATOR", "VIEWER"):
        response = await client.get(
            f"/api/v1/sites/{world.site_a.id}", headers=_auth(world, key)
        )
        assert response.status_code == 200, key
