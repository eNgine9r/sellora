from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.integration_connection import IntegrationStatus


class NovaPoshtaSettingsRequest(BaseModel):
    api_key: str = Field(min_length=8, max_length=255)
    sender_city_ref: str | None = None
    sender_warehouse_ref: str | None = None
    sender_counterparty_ref: str | None = None
    sender_contact_ref: str | None = None
    sender_phone: str | None = None


class NovaPoshtaSettingsResponse(BaseModel):
    provider: str = "NOVA_POSHTA"
    status: IntegrationStatus
    connection_name: str | None = None
    connected_at: datetime | None = None
    last_sync_at: datetime | None = None
    masked_api_key: str | None = None
    sender_city_ref: str | None = None
    sender_warehouse_ref: str | None = None
    sender_counterparty_ref: str | None = None
    sender_contact_ref: str | None = None
    sender_phone: str | None = None


class NovaPoshtaTestConnectionResponse(BaseModel):
    success: bool
    message: str
    status: IntegrationStatus


class NovaPoshtaDirectoryItem(BaseModel):
    ref: str
    description: str
    number: str | None = None


class NovaPoshtaTtnResponse(BaseModel):
    success: bool
    message: str
    tracking_number: str | None = None
    document_ref: str | None = None
    status: str | None = None
    errors: list[str] = Field(default_factory=list)


class NovaPoshtaStatusResponse(BaseModel):
    success: bool
    message: str
    tracking_number: str | None = None
    status: str | None = None
    synced_at: datetime | None = None
