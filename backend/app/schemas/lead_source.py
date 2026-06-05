from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LeadSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    is_active: bool = True


class LeadSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_active: bool | None = None


class LeadSourceResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
