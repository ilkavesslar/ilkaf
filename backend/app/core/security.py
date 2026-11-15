"""Authentication dependencies: session cookie/bearer extraction, validation, principal load."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    AuthenticationError,
    SessionValidator,
    get_token_validator,
    reset_token_validator,
    set_token_validator,
)
from app.core.config import get_settings
from app.core.db import get_db_session
from app.core.rbac import Principal
from app.services.identity import resolve_principal_from_session

__all__ = [
    "get_current_principal",
    "get_optional_principal",
    "require_authenticated",
    "set_token_validator",
    "reset_token_validator",
]


def _extract_session_token(request: Request) -> str | None:
    settings = get_settings()
    cookie_name = settings.auth_session_cookie_name
    if cookie_name in request.cookies:
        return request.cookies[cookie_name]
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


async def get_current_principal(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    validator: SessionValidator = Depends(get_token_validator),
) -> Principal:
    token = _extract_session_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = await validator.validate(token, session)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    principal = await resolve_principal_from_session(session, claims)
    request.state.principal = principal
    return principal


require_authenticated = get_current_principal


async def get_optional_principal(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    validator: SessionValidator = Depends(get_token_validator),
) -> Principal | None:
    if not _extract_session_token(request):
        return None
    try:
        return await get_current_principal(request, session, validator)
    except HTTPException:
        return None
