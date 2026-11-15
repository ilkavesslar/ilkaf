from uuid import uuid4

import pytest
from app.core.rbac import (
    PERMISSIONS,
    Principal,
    RoleName,
    has_permission,
    require_organization,
    require_permission,
    require_site,
)
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient


def _principal(**kwargs: object) -> Principal:
    defaults: dict[str, object] = {
        "user_id": uuid4(),
        "organization_id": uuid4(),
        "role": RoleName.OPERATOR,
        "site_ids": frozenset(),
    }
    defaults.update(kwargs)
    return Principal(**defaults)  # type: ignore[arg-type]


def test_viewer_cannot_ack() -> None:
    assert "incident.ack" not in PERMISSIONS[RoleName.VIEWER]
    assert has_permission(_principal(role=RoleName.OPERATOR), "incident.ack")
    assert not has_permission(_principal(role=RoleName.VIEWER), "incident.ack")


def test_all_sprint0_roles_defined() -> None:
    names = {role.value for role in RoleName}
    assert names == {
        "SYSTEM_ADMIN",
        "ORG_ADMIN",
        "SITE_MANAGER",
        "SAFETY_OFFICER",
        "OPERATOR",
        "VIEWER",
    }


def test_permission_matrix_sprint2() -> None:
    assert has_permission(_principal(role=RoleName.ORG_ADMIN), "sites:create")
    assert not has_permission(_principal(role=RoleName.VIEWER), "sites:create")
    assert not has_permission(_principal(role=RoleName.SITE_MANAGER), "sites:create")
    with pytest.raises(HTTPException) as denied:
        require_permission(_principal(role=RoleName.VIEWER), "sites:update")
    assert denied.value.status_code == 403


def test_require_organization_blocks_cross_tenant() -> None:
    org_a = uuid4()
    org_b = uuid4()
    operator = _principal(organization_id=org_a, role=RoleName.OPERATOR)
    require_organization(operator, org_a)
    with pytest.raises(HTTPException) as denied:
        require_organization(operator, org_b)
    assert denied.value.status_code == 403
    admin = _principal(organization_id=org_a, role=RoleName.SYSTEM_ADMIN)
    require_organization(admin, org_b)


def test_require_site_scopes_non_admin() -> None:
    org = uuid4()
    site_ok = uuid4()
    site_other = uuid4()
    operator = _principal(
        organization_id=org,
        role=RoleName.OPERATOR,
        site_ids=frozenset({site_ok}),
    )
    require_site(operator, org, site_ok)
    with pytest.raises(HTTPException):
        require_site(operator, org, site_other)
    org_admin = _principal(organization_id=org, role=RoleName.ORG_ADMIN, site_ids=frozenset())
    require_site(org_admin, org, site_other)


def test_me_route_returns_401() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "http_error"


def test_me_route_ignores_unsigned_authorization_header() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/me", headers={"Authorization": "Bearer x"})
    assert response.status_code == 401


def test_me_unversioned_alias_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.get("/api/me")
    assert response.status_code == 401


def test_boom_absent_outside_testing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    get_settings = pytest.importorskip("app.core.config").get_settings
    get_settings.cache_clear()
    from app.main import create_app

    application = create_app()
    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get("/__test/boom")
    assert response.status_code == 404
    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "testing")
    get_settings.cache_clear()
