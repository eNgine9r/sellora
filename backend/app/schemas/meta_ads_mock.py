from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MetaAdsMockIssueResponse(BaseModel):
    code: str
    message: str
    external_campaign_id: str | None = None


class MetaAdsMockAuditEventResponse(BaseModel):
    event: str
    provider: str = "meta_ads"
    workspace_id: UUID
    user_id: UUID | None = None
    outcome: str
    connection_mode: str = "mock"
    persisted: bool = False
    payload: dict[str, object] = Field(default_factory=dict)


class MetaTokenSafetyResponse(BaseModel):
    status: str
    masked_value: str
    fingerprint: str
    token_stored: bool = False
    raw_token_returned: bool = False
    message: str = ""


class MetaAdsMockStatusResponse(BaseModel):
    status: str
    provider: str = "meta_ads"
    workspace_id: UUID
    connection_mode: str = "mock"
    mock_api_enabled: bool = False
    connected: bool = False
    requires_live_setup: bool = True
    token_stored: bool = False
    live_api_enabled: bool = False
    message: str = ""
    issues: list[MetaAdsMockIssueResponse] = Field(default_factory=list)
    audit_event: MetaAdsMockAuditEventResponse | None = None


class MetaAdsMockStartResponse(BaseModel):
    status: str
    provider: str = "meta_ads"
    workspace_id: UUID
    connection_mode: str = "mock"
    authorization_url: str
    state_expires_at: datetime
    connected: bool = False
    requires_live_setup: bool = True
    token_stored: bool = False
    live_api_enabled: bool = False
    message: str = ""
    issues: list[MetaAdsMockIssueResponse] = Field(default_factory=list)
    audit_event: MetaAdsMockAuditEventResponse | None = None


class MetaAdsMockCallbackRequest(BaseModel):
    state: str
    code: str


class MetaAdsMockCallbackResponse(BaseModel):
    status: str
    provider: str = "meta_ads"
    workspace_id: UUID
    connection_mode: str = "mock"
    connected: bool = False
    requires_live_setup: bool = True
    token_stored: bool = False
    live_api_enabled: bool = False
    message: str = ""
    token_safety: MetaTokenSafetyResponse | None = None
    issues: list[MetaAdsMockIssueResponse] = Field(default_factory=list)
    audit_event: MetaAdsMockAuditEventResponse | None = None


class MetaAdsMockDisconnectResponse(BaseModel):
    status: str
    provider: str = "meta_ads"
    workspace_id: UUID
    connection_mode: str = "mock"
    connected: bool = False
    token_stored: bool = False
    live_api_enabled: bool = False
    message: str = ""
    issues: list[MetaAdsMockIssueResponse] = Field(default_factory=list)
    audit_event: MetaAdsMockAuditEventResponse | None = None
