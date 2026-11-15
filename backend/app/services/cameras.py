"""Camera metadata registry. No RTSP, credentials, or stream handles."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Permission, Principal, has_permission, has_site_access
from app.models import AuditLog, Camera, Site
from app.schemas.cameras import CameraCreate, CameraUpdate


async def _load_accessible_site(
    session: AsyncSession, principal: Principal, site_id: UUID
) -> Site:
    site = await session.get(Site, site_id)
    if site is None or not has_site_access(principal, site.organization_id, site.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="site not found")
    return site


async def list_cameras_for_site(
    session: AsyncSession, principal: Principal, site_id: UUID
) -> list[Camera]:
    site = await _load_accessible_site(session, principal, site_id)
    if not has_permission(principal, Permission.CAMERAS_READ, site.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    result = await session.scalars(
        select(Camera).where(Camera.site_id == site.id).order_by(Camera.name)
    )
    return list(result.all())


async def get_camera(session: AsyncSession, principal: Principal, camera_id: UUID) -> Camera:
    camera = await session.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="camera not found")
    if not has_site_access(principal, camera.organization_id, camera.site_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="camera not found")
    if not has_permission(principal, Permission.CAMERAS_READ, camera.site_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return camera


async def create_camera(
    session: AsyncSession, principal: Principal, site_id: UUID, payload: CameraCreate
) -> Camera:
    site = await _load_accessible_site(session, principal, site_id)
    if not has_permission(principal, Permission.CAMERAS_CREATE, site.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    camera = Camera(
        site_id=site.id,
        organization_id=site.organization_id,
        name=payload.name,
        code=payload.code,
        description=payload.description,
        location=payload.location,
        status=payload.status,
    )
    session.add(camera)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="camera code already exists at this site",
        ) from exc
    session.add(
        AuditLog(
            actor_user_id=principal.user_id,
            action="camera.create",
            entity_type="camera",
            entity_id=str(camera.id),
        )
    )
    await session.commit()
    await session.refresh(camera)
    return camera


async def update_camera(
    session: AsyncSession, principal: Principal, camera_id: UUID, payload: CameraUpdate
) -> Camera:
    camera = await session.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="camera not found")
    if not has_site_access(principal, camera.organization_id, camera.site_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="camera not found")
    if not has_permission(principal, Permission.CAMERAS_UPDATE, camera.site_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(camera, key, value)
    session.add(
        AuditLog(
            actor_user_id=principal.user_id,
            action="camera.update",
            entity_type="camera",
            entity_id=str(camera.id),
        )
    )
    await session.commit()
    await session.refresh(camera)
    return camera
