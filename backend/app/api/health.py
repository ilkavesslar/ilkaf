from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.db import check_database
from app.schemas.status import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe. Does not touch the database."""
    return HealthResponse(status="healthy")


@router.get("/ready")
async def ready() -> dict[str, str]:
    settings = get_settings()
    if not settings.resolved_database_url:
        raise HTTPException(status_code=503, detail="database not configured")
    try:
        await check_database()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ready", "database": "ok"}
