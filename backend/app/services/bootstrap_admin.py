"""Create the first SYSTEM_ADMIN. Refuses to replace an existing one."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.password import get_password_hasher
from app.core.rbac import RoleName
from app.models import Organization, Role, User

_EMAIL = TypeAdapter(EmailStr)


class BootstrapError(Exception):
    """The first admin was not created."""


def session_cookie_attributes(header: str) -> list[str]:
    """Drop the cookie value. Callers may print the returned attributes."""
    parts = [part.strip() for part in header.split(";") if part.strip()]
    return parts[1:]


def normalize_admin_email(email: str) -> str:
    try:
        parsed = _EMAIL.validate_python(email.strip())
    except ValidationError as exc:
        raise BootstrapError("email is not valid") from exc
    return str(parsed).strip().lower()


def require_admin_password(password: str) -> None:
    if not isinstance(password, str) or len(password) < 12 or password.strip() != password:
        raise BootstrapError(
            "password must be at least 12 characters and not start or end with a space"
        )


async def provision_first_admin(
    session: AsyncSession, email: str, password: str
) -> tuple[str, str]:
    """Insert one active SYSTEM_ADMIN and commit. Returns email and organization name."""
    normalized = normalize_admin_email(email)
    require_admin_password(password)
    admin_role = await session.scalar(select(Role).where(Role.name == RoleName.SYSTEM_ADMIN.value))
    if admin_role is None:
        raise BootstrapError("SYSTEM_ADMIN role is missing. Apply migrations first.")
    existing_admin = await session.scalar(
        select(User.id).where(User.role_id == admin_role.id).limit(1)
    )
    if existing_admin is not None:
        raise BootstrapError("A SYSTEM_ADMIN already exists")
    taken = await session.scalar(
        select(User.id).where(func.lower(User.email) == normalized).limit(1)
    )
    if taken is not None:
        raise BootstrapError("That email already belongs to an account")

    organization = await session.scalar(
        select(Organization).order_by(Organization.created_at, Organization.id).limit(1)
    )
    if organization is None:
        organization = Organization(name="ILKA")
        session.add(organization)
        await session.flush()
    organization_name = organization.name
    # Operator typed the address. Login does not send a verification message.
    user = User(
        organization_id=organization.id,
        role_id=admin_role.id,
        email=normalized,
        display_name=normalized.split("@", 1)[0][:200],
        disabled_at=None,
        email_verified=True,
        password_hash=get_password_hasher().hash(password),
        password_changed_at=datetime.now(UTC),
        failed_login_attempts=0,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise BootstrapError("Could not create the account") from None
    return normalized, organization_name
