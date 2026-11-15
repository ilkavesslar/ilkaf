"""Load ILKA users from validated session claims. Users are provisioned, not invented."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import SessionClaims
from app.core.rbac import Principal, RoleName
from app.models import User, UserSiteAssignment


def _unprovisioned() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identity is not provisioned",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def resolve_principal_from_session(
    session: AsyncSession,
    claims: SessionClaims,
) -> Principal:
    user = await _find_user(session, claims)
    if user is None:
        raise _unprovisioned()
    if user.disabled_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    if claims.name and not user.display_name:
        user.display_name = claims.name
        await session.commit()
        await session.refresh(user)

    try:
        role_name = RoleName(user.role.name)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role is not recognized",
        ) from None

    assignments = (
        await session.scalars(
            select(UserSiteAssignment)
            .options(selectinload(UserSiteAssignment.role))
            .where(UserSiteAssignment.user_id == user.id)
        )
    ).all()
    site_ids = frozenset(item.site_id for item in assignments)
    site_roles: list[tuple[UUID, RoleName]] = []
    for item in assignments:
        if item.role is not None:
            try:
                site_roles.append((item.site_id, RoleName(item.role.name)))
            except ValueError:
                site_roles.append((item.site_id, role_name))
        else:
            site_roles.append((item.site_id, role_name))

    return Principal(
        user_id=user.id,
        organization_id=user.organization_id,
        role=role_name,
        email=user.email,
        display_name=user.display_name or claims.name or user.email,
        site_ids=site_ids,
        site_roles=tuple(site_roles),
    )


async def _find_user(
    session: AsyncSession,
    claims: SessionClaims,
) -> User | None:
    """Return the user by explicit user_id, then by email."""
    if claims.user_id is not None:
        return await session.scalar(
            select(User)
            .options(selectinload(User.role))
            .where(User.id == claims.user_id)
        )
    if not claims.email:
        return None
    return await session.scalar(
        select(User)
        .options(selectinload(User.role))
        .where(func.lower(User.email) == claims.email.lower())
    )
