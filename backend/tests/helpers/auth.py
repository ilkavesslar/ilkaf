"""Test helpers for ILKA custom authentication.

Creates real server-side sessions for test users. Never used in production.
"""

from __future__ import annotations

from app.core.password import get_password_hasher
from app.models import User
from app.services.auth_service import AuthenticationService
from sqlalchemy.ext.asyncio import AsyncSession


async def set_user_password(session: AsyncSession, user: User, password: str) -> None:
    """Set a password hash for a test user."""
    hasher = get_password_hasher()
    user.password_hash = hasher.hash(password)
    await session.commit()


async def create_test_session(
    session: AsyncSession,
    user: User,
) -> str:
    """Create a real server-side session for a test user and return the raw token."""
    service = AuthenticationService()
    raw_token, _record = await service.create_session(session, user)
    return raw_token


def session_cookie_header(token: str, cookie_name: str = "ilka_session") -> dict[str, str]:
    """Return a Cookie header suitable for AsyncClient."""
    return {"Cookie": f"{cookie_name}={token}"}
