import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

CameraStatus = Literal["ACTIVE", "INACTIVE", "MAINTENANCE"]

_CAMERA_CODE = r"^[A-Za-z0-9][A-Za-z0-9_-]{1,62}$"


class CameraCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=2, max_length=64)
    description: str = Field(default="", max_length=1000)
    location: str = Field(default="", max_length=200)
    status: CameraStatus = "ACTIVE"

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, value: str) -> str:
        code = value.strip().upper()
        if not re.fullmatch(_CAMERA_CODE, code):
            raise ValueError("camera code must be alphanumeric with optional hyphen or underscore")
        return code

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name is required")
        return stripped


class CameraUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    location: str | None = Field(default=None, max_length=200)
    status: CameraStatus | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("name is required")
        return stripped


class CameraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    site_id: UUID
    organization_id: UUID
    name: str
    code: str
    description: str
    location: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
