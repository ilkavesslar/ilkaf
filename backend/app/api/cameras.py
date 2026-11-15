from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Principal
from app.core.security import get_current_principal
from app.db.database import get_db_session
from app.schemas.cameras import CameraResponse, CameraUpdate
from app.services import cameras as camera_service

router = APIRouter(
    tags=["cameras"],
    dependencies=[Depends(get_current_principal)],
)


@router.get("/cameras/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> CameraResponse:
    row = await camera_service.get_camera(session, principal, camera_id)
    return CameraResponse.model_validate(row)


@router.patch("/cameras/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: UUID,
    payload: CameraUpdate,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> CameraResponse:
    row = await camera_service.update_camera(session, principal, camera_id, payload)
    return CameraResponse.model_validate(row)
