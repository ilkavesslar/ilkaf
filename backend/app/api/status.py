from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.status import StatusResponse

router = APIRouter()


@router.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    """Public process status. Credentials and connection strings are never included."""
    settings = get_settings()
    return StatusResponse(
        application=settings.app_name,
        environment=settings.environment,
        status="operational",
    )
