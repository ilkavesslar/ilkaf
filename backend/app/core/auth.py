"""Custom session authentication validation interface.

ILKA manages its own sessions. This module defines the validator protocol used
by the security dependency. The default production validator looks up opaque
session tokens in the database.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class AuthenticationError(Exception):
    """Raised when a session token is missing, malformed, invalid, or revoked."""


@dataclass(frozen=True)
class SessionClaims:
    """Claims extracted from an authenticated session token."""

    user_id: UUID | None
    email: str | None
    name: str | None
    session_id: UUID | None


class SessionValidator(Protocol):
    async def validate(self, token: str, session: AsyncSession) -> SessionClaims: ...


class SessionValidatorImpl:
    """Production session validator.

    Opaque session tokens are looked up in the server-side session store. The
    raw token is never persisted; only its SHA-256 hash is stored.
    """

    async def validate(self, token: str, session: AsyncSession) -> SessionClaims:
        from app.services.auth_service import AuthenticationService

        service = AuthenticationService()
        user_session = await service.validate_session(session, token)
        if user_session is None:
            raise AuthenticationError("invalid or expired session")
        return SessionClaims(
            user_id=user_session.user_id,
            email=None,
            name=None,
            session_id=user_session.id,
        )


def build_session_validator() -> SessionValidator:
    """Return the production session validator."""
    return SessionValidatorImpl()


_validator: SessionValidator | None = None


def get_token_validator() -> SessionValidator:
    global _validator
    if _validator is None:
        _validator = build_session_validator()
    return _validator


def set_token_validator(validator: SessionValidator | None) -> None:
    """Test hook. Production code must not call this."""
    global _validator
    _validator = validator


def reset_token_validator() -> None:
    set_token_validator(None)


# Backwards-compatible alias for code that expects the token validator name.
TokenValidator = SessionValidator
