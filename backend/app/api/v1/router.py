from fastapi import APIRouter

from app.api import auth, cameras, demo_observations, detection, lab_cameras, sites, users

router = APIRouter()


@router.get("/status")
async def api_status() -> dict[str, str]:
    return {"api": "v1", "status": "ok"}


router.include_router(users.router)
router.include_router(auth.router)
router.include_router(sites.router)
router.include_router(cameras.router)
router.include_router(demo_observations.router)
router.include_router(detection.router)
router.include_router(lab_cameras.router)
