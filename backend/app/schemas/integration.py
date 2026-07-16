from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.integration_connection import IntegrationStatus


class NovaPoshtaSettingsRequest(BaseModel):
    api_key: str | None = Field(default=None, min_length=8, max_length=255)
    sender_city_ref: str | None = None
    sender_warehouse_ref: str | None = None
    sender_counterparty_ref: str | None = None
    sender_contact_ref: str | None = None
    sender_phone: str | None = None


class NovaPoshtaWritePermissionRequest(BaseModel):
    allowed: bool


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
    environment_capability: bool = False
    workspace_permission: bool = False
    provider_writes_enabled: bool = False
    sender_configured: bool = False
    connection_verified: bool = False
    write_blockers: list[str] = Field(default_factory=list)


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
    operation_state: str | None = None
    reused_existing_result: bool = False
    reconciliation_attempted: bool = False
    manual_reconciliation_required: bool = False
    blind_retry_blocked: bool = False
    errors: list[str] = Field(default_factory=list)


class NovaPoshtaStatusResponse(BaseModel):
    success: bool
    message: str
    tracking_number: str | None = None
    status: str | None = None
    raw_status: str | None = None
    normalized_status: str | None = None
    manual_review_required: bool = False
    synced_at: datetime | None = None
