from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.meta_ad_connection import MetaAdConnectionStatus


class MetaAdsConnectionAuditEventResponse(BaseModel):
    event: str
    provider: str = "meta_ads"
    workspace_id: UUID
    user_id: UUID | None = None
    outcome: str
    persisted: bool = False
    payload: dict[str, object] = Field(default_factory=dict)


class MetaAdsConnectionStatusResponse(BaseModel):
    provider: str = "meta_ads"
    workspace_id: UUID
    connection_status: MetaAdConnectionStatus
    connected: bool = False
    live_oauth_enabled: bool = False
    connections_enabled: bool = False
    token_storage_enabled: bool = False
    sync_enabled: bool = False
    configured: bool = False
    reason: str | None = None
    message: str = "Meta Ads connection is not available yet."
    account_name: str | None = None
    currency: str | None = None
    timezone: str | None = None
    external_ad_account_id_masked: str | None = None
    token_fingerprint: str | None = None
    token_expires_at: datetime | None = None
    connected_at: datetime | None = None
    disconnected_at: datetime | None = None
    last_synced_at: datetime | None = None
    audit_event: MetaAdsConnectionAuditEventResponse | None = None

    model_config = ConfigDict(use_enum_values=True)


class MetaAdsOAuthStartResponse(MetaAdsConnectionStatusResponse):
    authorization_url: str | None = None
    state_expires_at: datetime | None = None


class MetaAdsOAuthCallbackRequest(BaseModel):
    state: str
    code: str


class MetaAdsOAuthCallbackResponse(MetaAdsConnectionStatusResponse):
    token_stored: bool = False


class MetaAdsDisconnectResponse(MetaAdsConnectionStatusResponse):
    disconnected: bool = True
