"""Authenticated detection status. Does not start inference or expose model paths."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.lab_cameras import authorize_lab_camera
from app.core.rbac import Permission, Principal, require_permission
from app.core.security import get_current_principal
from app.db.database import get_db_session
from app.schemas.detection import (
    DetectionCapabilitiesResponse,
    DetectionCapabilityOut,
    LiveObservationsResponse,
)
from app.services import cameras as camera_service
from app.services.detection_state import get_detection_state

router = APIRouter(prefix="/detection", tags=["detection"])


def _capabilities():
    root = str(Path(__file__).resolve().parents[3])
    if root not in sys.path:
        sys.path.insert(0, root)
    from cv.capabilities import detection_capabilities

    return detection_capabilities()


def _camera_uuid(camera_id: str) -> UUID | None:
    try:
        return UUID(camera_id)
    except ValueError:
        return None


async def _authorize_camera(
    principal: Principal,
    camera_id: str | None,
    session: AsyncSession,
) -> str:
    require_permission(principal, Permission.CAMERAS_READ)
    if camera_id is None or not camera_id.strip():
        raise HTTPException(status_code=400, detail="camera_id is required")
    target = camera_id.strip()
    parsed = _camera_uuid(target)
    if parsed is not None:
        await camera_service.get_camera(session, principal, parsed)
        return target
    authorize_lab_camera(principal, target)
    return target


@router.get("/capabilities", response_model=DetectionCapabilitiesResponse)
async def read_detection_capabilities(
    principal: Principal = Depends(get_current_principal),
) -> DetectionCapabilitiesResponse:
    require_permission(principal, Permission.CAMERAS_READ)
    return DetectionCapabilitiesResponse(
        capabilities=[
            DetectionCapabilityOut(
                capability_id=item.capability_id,
                label=item.label,
                status=item.status,
                detail=item.detail,
            )
            for item in _capabilities()
        ]
    )


@router.get("/observations", response_model=LiveObservationsResponse)
async def read_live_observations(
    camera_id: str | None = None,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> LiveObservationsResponse:
    target = await _authorize_camera(principal, camera_id, session)
    stored = get_detection_state().read(target)
    if stored is None:
        return LiveObservationsResponse()
    return LiveObservationsResponse(status=stored.status, detail=stored.detail, items=stored.items)
