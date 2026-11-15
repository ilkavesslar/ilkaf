"""ILKA custom authentication and session management service."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings, get_settings
from app.core.password import PasswordHasherProtocol, get_password_hasher
from app.models import AuditLog, User, UserSession

logger = logging.getLogger("ilka.auth")


class AuthenticationServiceError(Exception):
    """Raised when an authentication operation fails."""


# Generic public-facing message to avoid user enumeration.
_INVALID_CREDENTIALS = "Invalid email or password"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _ensure_utc(dt: datetime | None) -> datetime | None:
    """Return an offset-aware UTC datetime, treating naive values as UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _hash_session_token(token: str) -> str:
    """Return a SHA-256 hash of an opaque session token.

    The token itself has high entropy (32 bytes from secrets.token_urlsafe).
    SHA-256 is used here for fast, deterministic lookup without storing the raw
    token in PostgreSQL.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


class AuthenticationService:
    """Implementation of ILKA-managed credential authentication and sessions."""

    def __init__(
        self,
        hasher: PasswordHasherProtocol | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._hasher = hasher or get_password_hasher()
        self._settings = settings or get_settings()

    async def authenticate_by_credentials(
        self,
        session: AsyncSession,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        """Verify email/password and return the matching user.

        Raises AuthenticationServiceError for any failure, with a generic
        message to avoid user enumeration.
        """
        user = await session.scalar(
            select(User)
            .options(selectinload(User.role))
            .where(User.email == _normalize_email(email))
        )

        if user is None:
            await self._audit(
                session, None, "auth.login.failure", ip_address=ip_address, user_agent=user_agent
            )
            raise AuthenticationServiceError(_INVALID_CREDENTIALS)

        if user.locked_until is not None and _ensure_utc(user.locked_until) > _utc_now():
            await self._audit(
                session,
                user.id,
                "auth.login.failure",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise AuthenticationServiceError(_INVALID_CREDENTIALS)

        if not user.password_hash:
            await self._audit(
                session,
                user.id,
                "auth.login.failure",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise AuthenticationServiceError(_INVALID_CREDENTIALS)

        if not self._hasher.verify(password, user.password_hash):
            await self._increment_failed_login(session, user)
            await self._audit(
                session,
                user.id,
                "auth.login.failure",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise AuthenticationServiceError(_INVALID_CREDENTIALS)

        if user.disabled_at is not None:
            await self._audit(
                session,
                user.id,
                "auth.login.failure",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise AuthenticationServiceError(_INVALID_CREDENTIALS)

        await self._reset_failed_login(session, user)
        await self._audit(
            session,
            user.id,
            "auth.login.success",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return user

    async def create_session(
        self,
        session: AsyncSession,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, UserSession]:
        """Create a new server-side session and return the raw token + record."""
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_session_token(raw_token)
        expires_at = _utc_now() + timedelta(
            days=self._settings.auth_refresh_token_expire_days
        )
        record = UserSession(
            user_id=user.id,
            refresh_token_hash=token_hash,
            expires_at=expires_at,
            ip_address=(ip_address or "")[:64] if ip_address else None,
            user_agent=(user_agent or "")[:500] if user_agent else None,
        )
        session.add(record)
        await session.flush()
        await session.commit()
        await session.refresh(record)
        return raw_token, record

    async def validate_session(
        self,
        session: AsyncSession,
        token: str,
    ) -> UserSession | None:
        """Return the session record if the token is valid, unexpired, and not revoked."""
        if not isinstance(token, str) or not token:
            return None
        token_hash = _hash_session_token(token)
        result = await session.scalar(
            select(UserSession).where(UserSession.refresh_token_hash == token_hash)
        )
        if result is None or result.revoked_at is not None:
            return None
        if _ensure_utc(result.expires_at) <= _utc_now():
            return None
        return result

    async def revoke_session(
        self,
        session: AsyncSession,
        token: str,
    ) -> UUID | None:
        """Revoke a session by token hash. Returns the user_id if a session was revoked."""
        token_hash = _hash_session_token(token)
        record = await session.scalar(
            select(UserSession).where(
                UserSession.refresh_token_hash == token_hash,
                UserSession.revoked_at.is_(None),
            )
        )
        if record is None:
            return None
        user_id = record.user_id
        record.revoked_at = _utc_now()
        await session.commit()
        return user_id

    async def _increment_failed_login(
        self,
        session: AsyncSession,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        user.failed_login_attempts += 1
        threshold = self._settings.auth_max_failed_logins
        if user.failed_login_attempts >= threshold:
            user.locked_until = _utc_now() + timedelta(
                minutes=self._settings.auth_lockout_minutes
            )
            await self._audit(
                session,
                user.id,
                "auth.account_locked",
                ip_address=ip_address,
                user_agent=user_agent,
            )
        await session.commit()

    async def _reset_failed_login(
        self,
        session: AsyncSession,
        user: User,
    ) -> None:
        if user.failed_login_attempts != 0 or user.locked_until is not None:
            user.failed_login_attempts = 0
            user.locked_until = None
            await session.commit()

    async def _audit(
        self,
        session: AsyncSession,
        user_id: UUID | None,
        action: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Append an authentication audit record.

        Audit failures are logged but never allowed to block authentication
        decisions or account lockout.
        """
        record = AuditLog(
            actor_user_id=user_id,
            action=action,
            entity_type="user",
            entity_id=str(user_id) if user_id else "",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.add(record)
        try:
            await session.flush()
            await session.commit()
        except Exception:
            # Audit logging must never break authentication.
            logger.exception("audit_log_failed")


def get_auth_service() -> AuthenticationService:
    return AuthenticationService()
