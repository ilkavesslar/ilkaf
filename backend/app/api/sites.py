from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Principal
from app.core.security import get_current_principal
from app.db.database import get_db_session
from app.schemas.cameras import CameraCreate, CameraResponse
from app.schemas.sites import SiteCreate, SiteResponse, SiteUpdate
from app.services import cameras as camera_service
from app.services import sites as site_service

router = APIRouter(
    tags=["sites"],
    dependencies=[Depends(get_current_principal)],
)


@router.get("/sites", response_model=list[SiteResponse])
async def list_sites(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> list[SiteResponse]:
    rows = await site_service.list_sites(session, principal)
    return [SiteResponse.model_validate(row) for row in rows]


@router.post("/sites", response_model=SiteResponse, status_code=201)
async def create_site(
    payload: SiteCreate,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> SiteResponse:
    row = await site_service.create_site(session, principal, payload)
    return SiteResponse.model_validate(row)


@router.get("/sites/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> SiteResponse:
    row = await site_service.get_site(session, principal, site_id)
    return SiteResponse.model_validate(row)


@router.patch("/sites/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: UUID,
    payload: SiteUpdate,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> SiteResponse:
    row = await site_service.update_site(session, principal, site_id, payload)
    return SiteResponse.model_validate(row)


@router.get("/sites/{site_id}/cameras", response_model=list[CameraResponse])
async def list_site_cameras(
    site_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> list[CameraResponse]:
    rows = await camera_service.list_cameras_for_site(session, principal, site_id)
    return [CameraResponse.model_validate(row) for row in rows]


@router.post("/sites/{site_id}/cameras", response_model=CameraResponse, status_code=201)
async def create_site_camera(
    site_id: UUID,
    payload: CameraCreate,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> CameraResponse:
    row = await camera_service.create_camera(session, principal, site_id, payload)
    return CameraResponse.model_validate(row)
