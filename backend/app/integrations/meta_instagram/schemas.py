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
