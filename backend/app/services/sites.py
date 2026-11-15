"""Site listing and mutations with query-layer scope enforcement."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import (
    Permission,
    Principal,
    RoleName,
    has_permission,
    has_site_access,
)
from app.models import AuditLog, Site
from app.schemas.sites import SiteCreate, SiteUpdate


def scoped_sites_query(principal: Principal) -> Select[tuple[Site]]:
    query = select(Site)
    if principal.role == RoleName.SYSTEM_ADMIN:
        return query.order_by(Site.name)
    query = query.where(Site.organization_id == principal.organization_id)
    if principal.role != RoleName.ORG_ADMIN:
        if not principal.site_ids:
            return query.where(Site.id.is_(None))
        query = query.where(Site.id.in_(principal.site_ids))
    return query.order_by(Site.name)


async def list_sites(session: AsyncSession, principal: Principal) -> list[Site]:
    if not has_permission(principal, Permission.SITES_READ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    result = await session.scalars(scoped_sites_query(principal))
    return list(result.all())


async def get_site(session: AsyncSession, principal: Principal, site_id: UUID) -> Site:
    if not has_permission(principal, Permission.SITES_READ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    site = await session.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="site not found")
    if not has_site_access(principal, site.organization_id, site.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="site not found")
    if not has_permission(principal, Permission.SITES_READ, site.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return site


async def create_site(session: AsyncSession, principal: Principal, payload: SiteCreate) -> Site:
    if not has_permission(principal, Permission.SITES_CREATE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    organization_id = principal.organization_id
    if principal.role == RoleName.SYSTEM_ADMIN and payload.organization_id is not None:
        organization_id = payload.organization_id
    site = Site(
        organization_id=organization_id,
        name=payload.name,
        code=payload.code,
        description=payload.description,
        timezone=payload.timezone,
        is_active=payload.is_active,
    )
    session.add(site)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="site code already exists",
        ) from exc
    session.add(
        AuditLog(
            actor_user_id=principal.user_id,
            action="site.create",
            entity_type="site",
            entity_id=str(site.id),
        )
    )
    await session.commit()
    await session.refresh(site)
    return site


async def update_site(
    session: AsyncSession, principal: Principal, site_id: UUID, payload: SiteUpdate
) -> Site:
    site = await session.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="site not found")
    if not has_site_access(principal, site.organization_id, site.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="site not found")
    if not has_permission(principal, Permission.SITES_UPDATE, site.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(site, key, value)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="site code already exists",
        ) from exc
    session.add(
        AuditLog(
            actor_user_id=principal.user_id,
            action="site.update",
            entity_type="site",
            entity_id=str(site.id),
        )
    )
    await session.commit()
    await session.refresh(site)
    return site
