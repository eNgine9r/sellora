from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class InstagramConnectResponse(BaseModel):
    authorization_url: str
    expires_at: datetime

class InstagramConnectionStatusResponse(BaseModel):
    workspace_id: UUID
    status: str
    instagram_username: str | None = None
    instagram_account_type: str | None = None
    granted_permissions: list[str] = Field(default_factory=list)
    subscribed_webhook_fields: list[str] = Field(default_factory=list)
    token_expires_at: datetime | None = None
    connected_at: datetime | None = None
    disconnected_at: datetime | None = None
    last_webhook_at: datetime | None = None
    last_message_received_at: datetime | None = None
    last_message_sent_at: datetime | None = None
    token_present: bool = False
    send_enabled: bool = False
    auto_send_enabled: bool = False
    webhook_active: bool = False
    confirmed_webhook_fields: list[str] = Field(default_factory=list)
    missing_webhook_fields: list[str] = Field(default_factory=list)
    callback_configured: bool = False
    verify_token_configured: bool = False
    account_subscription_active: bool = False
    required_fields_confirmed: bool = False
    webhook_processing_enabled: bool = False
    last_error_code: str | None = None
    last_error_message: str | None = None

class InstagramOAuthCallbackResponse(BaseModel):
    status: str
    connected: bool
    instagram_username: str | None = None

class InstagramDisconnectResponse(BaseModel):
    status: str
    disconnected: bool

class InstagramValidateResponse(BaseModel):
    status: str
    permission_ok: bool
    token_present: bool

class InstagramHistorySyncRequest(BaseModel):
    conversation_limit: int = Field(default=100, ge=1, le=500)
    messages_per_conversation: int = Field(default=20, ge=1, le=20)

class InstagramHistorySyncResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    instagram_connection_id: UUID
    status: str
    conversation_limit: int
    messages_per_conversation: int
    conversation_pages_processed: int
    conversations_discovered: int
    conversations_synced: int
    messages_discovered: int
    messages_imported: int
    messages_existing: int
    messages_unavailable: int
    error_count: int
    rate_limit_count: int
    attempt_count: int
    last_error_code: str | None = None
    next_retry_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class ReplyPrepareRequest(BaseModel):
    message_text: str = Field(min_length=1, max_length=1000)
    human_agent_requested: bool = False

class ReplyPrepareResponse(BaseModel):
    ready: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    message_preview: str
    human_agent_eligible: bool = False

class ReplySendRequest(ReplyPrepareRequest):
    suggestion_id: UUID | None = None

class ReplySendResponse(BaseModel):
    operation_id: UUID
    status: str
    provider_message_id: str | None = None
    direct_message_id: UUID | None = None

class MessageOperationResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    conversation_id: UUID
    status: str
    provider_message_id: str | None = None
    direct_message_id: UUID | None = None
    manual_reconciliation_required: bool = False
    blind_retry_blocked: bool = False
    last_error_code: str | None = None

    model_config = {"from_attributes": True}