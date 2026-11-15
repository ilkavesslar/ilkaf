from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest
from app.core.config import get_settings
from app.main import app
from app.models import AuditLog, User, UserSession
from app.services.auth_service import (
    AuthenticationService,
    _ensure_utc,
    _hash_session_token,
    _utc_now,
)
from httpx import AsyncClient
from sqlalchemy import func, select
from tests.helpers.auth import session_cookie_header
from tests.helpers.identity import IdentityWorld


@asynccontextmanager
async def _test_db_session():
    """Yield the dependency-overridden app session."""
    from app.core.db import get_db_session

    generator = app.dependency_overrides[get_db_session]()
    session = await generator.__anext__()
    try:
        yield session
    finally:
        try:
            await generator.aclose()
        except Exception:
            pass


@pytest.fixture
async def auth_env_with_passwords(
    auth_env: tuple[AsyncClient, IdentityWorld],
) -> tuple[AsyncClient, IdentityWorld]:
    client, world = auth_env
    async with _test_db_session() as session:
        service = AuthenticationService()
        for key, user in world.users.items():
            db_user = await session.get(User, user.id)
            if db_user is None or db_user.password_hash:
                continue
            db_user.password_hash = service._hasher.hash(f"{key.lower()}-password")
        await session.commit()
    return client, world


async def _login(
    client: AsyncClient,
    email: str,
    password: str,
) -> tuple[int, dict]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return response.status_code, response.json()


@pytest.mark.asyncio
async def test_login_success_and_session_cookie(
    auth_env_with_passwords: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env_with_passwords
    user = world.users["VIEWER"]
    status, body = await _login(client, user.email, "viewer-password")
    assert status == 200
    assert body["email"] == user.email
    assert body["id"] == str(user.id)
    assert "password_hash" not in body
    assert "password" not in body
    assert "access_token" not in body

    cookie_name = get_settings().auth_session_cookie_name
    assert client.cookies.get(cookie_name)

    me = await client.get("/api/v1/me")
    assert me.status_code == 200
    assert me.json()["email"] == user.email


@pytest.mark.asyncio
async def test_login_incorrect_password(
    auth_env_with_passwords: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env_with_passwords
    user = world.users["VIEWER"]
    status, body = await _login(client, user.email, "wrong-password")
    assert status == 401
    assert "password_hash" not in str(body)
    assert "viewer-password" not in str(body)
    assert body["error"]["message"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_unknown_user(
    auth_env_with_passwords: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, _world = auth_env_with_passwords
    status, body = await _login(client, "nobody@example.com", "any-password")
    assert status == 401
    assert body["error"]["message"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_disabled_user(
    auth_env_with_passwords: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env_with_passwords
    user = world.users["INACTIVE"]
    status, _body = await _login(client, user.email, "inactive-password")
    assert status == 401


@pytest.mark.asyncio
async def test_login_lockout_after_repeated_failures(
    auth_env_with_passwords: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env_with_passwords
    user = world.users["OPERATOR"]
    for _ in range(get_settings().auth_max_failed_logins):
        status, _body = await _login(client, user.email, "wrong")
        assert status == 401

    status, _body = await _login(client, user.email, "operator-password")
    assert status == 401

    async with _test_db_session() as session:
        refreshed = await session.get(User, user.id)
        assert refreshed is not None
        assert refreshed.failed_login_attempts >= get_settings().auth_max_failed_logins
        assert refreshed.locked_until is not None
        assert _ensure_utc(refreshed.locked_until) > _utc_now()


@pytest.mark.asyncio
async def test_login_resets_failed_attempts(
    auth_env_with_passwords: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env_with_passwords
    user = world.users["SITE_MANAGER"]
    await _login(client, user.email, "wrong")
    status, _body = await _login(client, user.email, "site_manager-password")
    assert status == 200

    async with _test_db_session() as session:
        refreshed = await session.get(User, user.id)
        assert refreshed is not None
        assert refreshed.failed_login_attempts == 0
        assert refreshed.locked_until is None


@pytest.mark.asyncio
async def test_expired_session_is_rejected(
    auth_env_with_passwords: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env_with_passwords
    token = ""
    async with _test_db_session() as session:
        user = world.users["VIEWER"]
        service = AuthenticationService()
        token, record = await service.create_session(session, user)
        record.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await session.commit()

    response = await client.get(
        "/api/v1/me",
        headers=session_cookie_header(token),
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_revoked_session_is_rejected(
    auth_env_with_passwords: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env_with_passwords
    token = ""
    async with _test_db_session() as session:
        user = world.users["VIEWER"]
        service = AuthenticationService()
        token, _record = await service.create_session(session, user)
        await service.revoke_session(session, token)

    response = await client.get(
        "/api/v1/me",
        headers=session_cookie_header(token),
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_missing_or_malformed_session_rejected(
    auth_env_with_passwords: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, _world = auth_env_with_passwords
    missing = await client.get("/api/v1/me")
    assert missing.status_code == 401
    bad = await client.get(
        "/api/v1/me",
        headers=session_cookie_header("not-a-token"),
    )
    assert bad.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_session_and_clears_cookie(
    auth_env_with_passwords: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env_with_passwords
    user = world.users["VIEWER"]
    status, _body = await _login(client, user.email, "viewer-password")
    assert status == 200

    cookie_name = get_settings().auth_session_cookie_name
    assert client.cookies.get(cookie_name)

    logout = await client.post("/api/v1/auth/logout", json={})
    assert logout.status_code == 200
    assert not client.cookies.get(cookie_name)

    async with _test_db_session() as session:
        revoked_count = await session.scalar(
            select(func.count()).select_from(UserSession).where(
                UserSession.user_id == user.id,
                UserSession.revoked_at.is_not(None),
            )
        )
        assert revoked_count and revoked_count >= 1


@pytest.mark.asyncio
async def test_logout_without_cookie_is_safe(
    auth_env_with_passwords: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, _world = auth_env_with_passwords
    response = await client.post("/api/v1/auth/logout", json={})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_session_token_is_stored_as_hash(
    auth_env_with_passwords: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env_with_passwords
    user = world.users["VIEWER"]
    status, _body = await _login(client, user.email, "viewer-password")
    assert status == 200

    raw_cookie = client.cookies.get(get_settings().auth_session_cookie_name)
    assert raw_cookie is not None

    async with _test_db_session() as session:
        stored = await session.scalar(
            select(UserSession).where(
                UserSession.refresh_token_hash == _hash_session_token(raw_cookie)
            )
        )
        assert stored is not None
        assert stored.refresh_token_hash != raw_cookie
        assert stored.refresh_token_hash == _hash_session_token(raw_cookie)


@pytest.mark.asyncio
async def test_password_hash_not_returned_by_login_or_me(
    auth_env_with_passwords: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env_with_passwords
    user = world.users["VIEWER"]
    status, body = await _login(client, user.email, "viewer-password")
    assert status == 200
    assert "password_hash" not in str(body)

    me = await client.get("/api/v1/me")
    assert me.status_code == 200
    assert "password_hash" not in str(me.json())


@pytest.mark.asyncio
async def test_audit_log_records_login_events(
    auth_env_with_passwords: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env_with_passwords
    user = world.users["ORG_ADMIN"]
    await _login(client, user.email, "org_admin-password")

    async with _test_db_session() as session:
        success_count = await session.scalar(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.actor_user_id == user.id,
                AuditLog.action == "auth.login.success",
            )
        )
        assert success_count == 1


@pytest.mark.asyncio
async def test_audit_log_records_failed_login_event(
    auth_env_with_passwords: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env_with_passwords
    user = world.users["VIEWER"]
    await _login(client, user.email, "wrong-password")

    async with _test_db_session() as session:
        failure_count = await session.scalar(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.actor_user_id == user.id,
                AuditLog.action == "auth.login.failure",
            )
        )
        assert failure_count == 1


@pytest.mark.asyncio
async def test_audit_log_records_logout_event(
    auth_env_with_passwords: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env_with_passwords
    user = world.users["VIEWER"]
    await _login(client, user.email, "viewer-password")
    await client.post("/api/v1/auth/logout", json={})

    async with _test_db_session() as session:
        logout_count = await session.scalar(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.actor_user_id == user.id,
                AuditLog.action == "auth.logout",
            )
        )
        assert logout_count == 1


@pytest.mark.asyncio
async def test_rbac_still_enforced_after_login(
    auth_env_with_passwords: tuple[AsyncClient, IdentityWorld],
) -> None:
    client, world = auth_env_with_passwords
    user = world.users["VIEWER"]
    status, _body = await _login(client, user.email, "viewer-password")
    assert status == 200

    denied = await client.post(
        "/api/v1/sites",
        json={"name": "Packing", "code": "PACK"},
    )
    assert denied.status_code == 403
