"""Authenticated lab API for one local MP4 person-detection run.

Person observations are not incidents. The route does not accept stream URLs
or credentials, and it does not create incident records.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.core.rbac import Permission, Principal, require_permission
from app.core.security import get_current_principal
from app.schemas.demo_observations import DemoObservationsResponse, DemoRunRequest
from app.services.demo_observations import DemoRunError, execute_demo_run, load_snapshot

router = APIRouter(prefix="/demo/person-observations", tags=["demo-observations"])

_MESSAGES = {
    "video_missing": "The local demo video is not available",
    "video_unreadable": "The local demo video could not be read",
    "weights_missing": "Person detector weights are not available",
    "weights_rejected": "Person detector weights failed the integrity check",
    "runtime_missing": "The person detector runtime is not available",
    "inference_failed": "Person detection failed for the local demo video",
    "invalid_observation": "A demo observation failed validation",
    "invalid_frame_count": "max_frames must be from 1 to 30",
    "store_unreadable": "The demo observation cache could not be read",
}


def _http_error(exc: DemoRunError) -> HTTPException:
    status = 400
    if exc.code in {"runtime_missing", "inference_failed", "store_unreadable"}:
        status = 503
    return HTTPException(status_code=status, detail=_MESSAGES.get(exc.code, "Demo run failed"))


@router.get("", response_model=DemoObservationsResponse)
async def read_demo_observations(
    principal: Principal = Depends(get_current_principal),
) -> DemoObservationsResponse:
    require_permission(principal, Permission.SAFETY_READ)
    try:
        return load_snapshot()
    except DemoRunError as exc:
        raise _http_error(exc) from None


@router.post("/runs", response_model=DemoObservationsResponse)
async def run_demo_observations(
    payload: DemoRunRequest,
    principal: Principal = Depends(get_current_principal),
) -> DemoObservationsResponse:
    require_permission(principal, Permission.SAFETY_MANAGE)
    try:
        return await asyncio.to_thread(execute_demo_run, None, max_frames=payload.max_frames)
    except DemoRunError as exc:
        raise _http_error(exc) from None
