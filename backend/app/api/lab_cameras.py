"""Development-only MJPEG preview. RTSP credentials stay on the server.

Production returns 404. A configured organization and site are enforced with
the existing site check. The response never includes a stream URL or password.
"""

from __future__ import annotations

import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.core.rbac import Permission, Principal, require_permission, require_site
from app.core.security import get_current_principal
from app.services.lab_camera_streams import (
    LabCameraError,
    get_lab_camera_hub,
    lab_cameras_available,
)

router = APIRouter(prefix="/lab/cameras", tags=["lab-cameras"])


def authorize_lab_camera(principal: Principal, camera_id: str) -> None:
    """Allow a known lab camera only when the existing lab guard allows it."""

    try:
        get_lab_camera_hub().camera(camera_id)
    except LabCameraError:
        raise HTTPException(status_code=404, detail="camera not found") from None
    _guard(principal)


def _guard(principal: Principal) -> None:
    if not lab_cameras_available():
        raise HTTPException(status_code=404, detail="not found")
    require_permission(principal, Permission.CAMERAS_READ)
    settings = get_settings()
    organization = settings.lab_camera_organization_id.strip()
    site = settings.lab_camera_site_id.strip()
    if organization and site:
        require_site(principal, UUID(organization), UUID(site))
    elif settings.environment not in {"development", "testing"}:
        raise HTTPException(status_code=403, detail="forbidden")


@router.get("")
async def list_lab_cameras(
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    _guard(principal)
    hub = get_lab_camera_hub()
    cameras = []
    for camera in hub.cameras():
        item = hub.health(camera.camera_id)
        cameras.append(
            {
                "camera_id": item.camera_id,
                "name": item.name,
                "host": item.host,
                "source_id": item.source_id,
                "state": item.state,
                "last_frame_at": item.last_frame_at.isoformat() if item.last_frame_at else None,
                "frame_width": item.frame_width,
                "frame_height": item.frame_height,
                "error": item.error,
            }
        )
    return {"cameras": cameras}


@router.get("/{camera_id}/mjpeg")
async def stream_lab_camera(
    camera_id: str,
    principal: Principal = Depends(get_current_principal),
) -> StreamingResponse:
    _guard(principal)
    hub = get_lab_camera_hub()
    try:
        hub.camera(camera_id)
    except LabCameraError:
        raise HTTPException(status_code=404, detail="not found") from None
    if not os.environ.get("ILKA_CAMERA_USERNAME") or not os.environ.get("ILKA_CAMERA_PASSWORD"):
        raise HTTPException(status_code=503, detail="camera account is not configured")
    return StreamingResponse(
        hub.multipart(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
