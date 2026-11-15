from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["healthy"]


class StatusResponse(BaseModel):
    """Public process status. Must never include secrets or credentials."""

    model_config = ConfigDict(extra="forbid")

    application: str
    environment: str
    status: Literal["operational"] = Field(default="operational")
