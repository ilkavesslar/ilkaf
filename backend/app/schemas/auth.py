"""Request/response schemas for the custom authentication endpoints."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    # Optional refresh token for explicit revocation of a server-side session.
    refresh_token: str | None = None


class MeResponse(BaseModel):
    id: str
    email: str
    name: str
    roles: list[str]
    sites: list[dict[str, object]]
