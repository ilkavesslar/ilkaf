import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

_SITE_CODE = r"^[A-Za-z0-9][A-Za-z0-9_-]{1,62}$"


class SiteSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str | None = None
    role: str | None = None


class MeResponse(BaseModel):
    id: UUID
    email: str
    name: str
    roles: list[str]
    sites: list[SiteSummary]


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=2, max_length=64)
    description: str = Field(default="", max_length=1000)
    timezone: str = Field(default="UTC", max_length=64)
    is_active: bool = True
    organization_id: UUID | None = None

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, value: str) -> str:
        code = value.strip().upper()
        if not re.fullmatch(_SITE_CODE, code):
            raise ValueError("site code must be alphanumeric with optional hyphen or underscore")
        return code

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name is required")
        return stripped


class SiteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, min_length=2, max_length=64)
    description: str | None = Field(default=None, max_length=1000)
    timezone: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return SiteCreate._normalize_code(value)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("name is required")
        return stripped


class SiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    code: str | None
    description: str
    timezone: str
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
