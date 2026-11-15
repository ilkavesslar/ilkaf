"""Custom authentication endpoints.

Login creates an HTTP-only session cookie. Logout revokes the server-side
session and clears the cookie. The /auth/me route returns the authenticated
principal without exposing password hashes or session tokens.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.rbac import Principal
from app.core.security import get_current_principal
from app.db.database import get_db_session
from app.schemas.auth import LoginRequest, LogoutRequest, MeResponse
from app.services.auth_service import (
    AuthenticationService,
    AuthenticationServiceError,
    get_auth_service,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(
    response: Response,
    token: str,
    settings: Settings,
) -> None:
    max_age_seconds = settings.auth_refresh_token_expire_days * 86_400
    response.set_cookie(
        key=settings.auth_session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.environment == "production",
        samesite=settings.auth_session_cookie_samesite,
        max_age=max_age_seconds,
        path="/",
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.auth_session_cookie_name,
        path="/",
    )


@router.post("/login", response_model=MeResponse)
async def login(
    response: Response,
    request: Request,
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
    service: AuthenticationService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> MeResponse:
    """Authenticate an email/password pair and set an HTTP-only session cookie."""
    try:
        user = await service.authenticate_by_credentials(
            session,
            payload.email,
            payload.password,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AuthenticationServiceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from None

    # Capture values before create_session commits and expires the instance.
    user_id = user.id
    email = user.email
    display_name = user.display_name
    role_name = user.role.name

    raw_token, _record = await service.create_session(
        session,
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_session_cookie(response, raw_token, settings)

    return MeResponse(
        id=str(user_id),
        email=email,
        name=display_name,
        roles=[role_name],
        sites=[],
    )


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    _payload: LogoutRequest,
    session: AsyncSession = Depends(get_db_session),
    service: AuthenticationService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """Revoke the current session and clear the browser cookie."""
    cookie_name = settings.auth_session_cookie_name
    token = request.cookies.get(cookie_name)
    if token:
        user_id = await service.revoke_session(session, token)
        if user_id:
            await service._audit(
                session,
                user_id,
                "auth.logout",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
    _clear_session_cookie(response, settings)
    return {"status": "ok"}


@router.get("/me", response_model=MeResponse)
async def read_auth_me(
    principal: Principal = Depends(get_current_principal),
) -> MeResponse:
    """Return the authenticated principal."""
    return MeResponse(
        id=str(principal.user_id),
        email=principal.email,
        name=principal.display_name,
        roles=[principal.role.value],
        sites=[
            {"id": str(site_id), "role": role.value}
            for site_id, role in principal.site_roles
        ],
    )
