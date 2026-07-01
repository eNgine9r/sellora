from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.lead import LeadStatus


class LeadCreate(BaseModel):
    instagram_username: str | None = Field(default=None, max_length=120)
    instagram_profile_url: str | None = Field(default=None, max_length=500)
    name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    lead_source_id: UUID | None = None
    campaign_id: UUID | None = None
    notes: str | None = None
    assigned_user_id: UUID | None = None
    expected_revenue: Decimal | None = Field(default=None, ge=0)
    first_contact_at: datetime | None = None
    last_contact_at: datetime | None = None


class LeadUpdate(BaseModel):
    instagram_username: str | None = Field(default=None, max_length=120)
    instagram_profile_url: str | None = Field(default=None, max_length=500)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    lead_source_id: UUID | None = None
    campaign_id: UUID | None = None
    status: LeadStatus | None = None
    notes: str | None = None
    assigned_user_id: UUID | None = None
    expected_revenue: Decimal | None = Field(default=None, ge=0)
    loss_reason: str | None = None
    first_contact_at: datetime | None = None
    last_contact_at: datetime | None = None

    @model_validator(mode="after")
    def require_loss_reason_when_lost(self) -> "LeadUpdate":
        if self.status == LeadStatus.LOST and not self.loss_reason:
            raise ValueError("loss_reason is required when status is LOST")
        return self


class LeadAssignRequest(BaseModel):
    assigned_user_id: UUID


class LeadMarkLostRequest(BaseModel):
    loss_reason: str = Field(min_length=1)


class LeadResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    instagram_username: str | None
    instagram_profile_url: str | None
    name: str
    phone: str | None
    lead_source_id: UUID | None
    campaign_id: UUID | None
    campaign_name: str | None = None
    status: LeadStatus
    notes: str | None
    assigned_user_id: UUID | None
    expected_revenue: Decimal | None
    loss_reason: str | None
    first_contact_at: datetime | None
    last_contact_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
