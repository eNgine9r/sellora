from __future__ import annotations

from datetime import date, datetime
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
    implemented: bool = True
    blockers: list[str] = Field(default_factory=list)
    can_connect: bool = False
    can_sync: bool = False
    account_selection_required: bool = False
    last_sync_attempt_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
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
    state: str = Field(min_length=1, max_length=2048)
    code: str = Field(min_length=1, max_length=4096)


class MetaAdsOAuthCallbackResponse(MetaAdsConnectionStatusResponse):
    token_stored: bool = False


class MetaAdsDisconnectResponse(MetaAdsConnectionStatusResponse):
    disconnected: bool = True


class MetaAdsAccountSelectionRequest(BaseModel):
    external_account_id: str = Field(pattern=r"^act_[0-9]{1,40}$")


class MetaAdsSyncRequest(BaseModel):
    date_from: date
    date_to: date


class MetaAdsAccountChoice(BaseModel):
    external_account_id: str
    name: str
    currency: str
    timezone: str
    selectable: bool
    reason: str | None = None


class MetaAdsAccountsResponse(BaseModel):
    accounts: list[MetaAdsAccountChoice]
    selected_account_id: str | None = None
    workspace_currency: str
    workspace_timezone: str


class MetaAdsSyncResponse(BaseModel):
    status: str
    campaigns_seen: int
    metrics_seen: int
    campaigns_created: int
    metrics_created: int
    metrics_updated: int
    date_from: date
    date_to: date
    currency: str
    timezone: str
    workspace_timezone: str
    last_synced_at: datetime
    spend_currency: str
    exchange_rate_source: str
    reach_measure: str = "not_imported"
