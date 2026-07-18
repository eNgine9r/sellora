from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class InstagramConnectionStatus(StrEnum):
    PENDING = "PENDING"
    CONNECTED = "CONNECTED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    PERMISSION_MISSING = "PERMISSION_MISSING"
    WEBHOOK_INACTIVE = "WEBHOOK_INACTIVE"
    RECONNECT_REQUIRED = "RECONNECT_REQUIRED"
    DISCONNECTED = "DISCONNECTED"
    FAILED = "FAILED"


class InstagramLoginType(StrEnum):
    INSTAGRAM_LOGIN = "INSTAGRAM_LOGIN"


class MetaWebhookEventStatus(StrEnum):
    RECEIVED = "RECEIVED"
    VERIFIED = "VERIFIED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    IGNORED = "IGNORED"
    RETRY_PENDING = "RETRY_PENDING"
    DEAD_LETTER = "DEAD_LETTER"
    FAILED_SAFE = "FAILED_SAFE"


class MetaMessageOperationStatus(StrEnum):
    PREPARED = "PREPARED"
    SENDING = "SENDING"
    PROVIDER_SUCCEEDED = "PROVIDER_SUCCEEDED"
    COMPLETED = "COMPLETED"
    RETRY_PENDING = "RETRY_PENDING"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    FAILED_SAFE = "FAILED_SAFE"
    CANCELLED = "CANCELLED"


class InstagramConnection(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "instagram_connections"
    __table_args__ = (UniqueConstraint("workspace_id", "instagram_account_id", name="uq_instagram_connections_workspace_account"),)

    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="INSTAGRAM")
    login_type: Mapped[str] = mapped_column(String(40), nullable=False, default=InstagramLoginType.INSTAGRAM_LOGIN.value)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=InstagramConnectionStatus.PENDING.value)
    instagram_account_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    instagram_username: Mapped[str | None] = mapped_column(String(160), nullable=True)
    instagram_account_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    meta_app_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    granted_permissions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    subscribed_webhook_fields: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    access_token_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token_nonce: Mapped[str | None] = mapped_column(String(120), nullable=True)
    access_token_key_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_webhook_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_message_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_message_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class MetaOAuthState(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, Base):
    __tablename__ = "meta_oauth_states"

    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    code_verifier_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    redirect_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MetaWebhookEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "meta_webhook_events"
    __table_args__ = (UniqueConstraint("provider", "event_external_id", name="uq_meta_webhook_events_provider_external_id"),)

    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="INSTAGRAM")
    workspace_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    instagram_connection_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("instagram_connections.id", ondelete="SET NULL"), nullable=True)
    event_external_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    object_type: Mapped[str] = mapped_column(String(80), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    event_date_bucket: Mapped[date | None] = mapped_column(Date, nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    signature_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=MetaWebhookEventStatus.RECEIVED.value)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    safe_error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    safe_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MetaMessageOperation(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "meta_message_operations"
    __table_args__ = (UniqueConstraint("workspace_id", "idempotency_key", name="uq_meta_message_operations_workspace_idempotency_key"),)

    instagram_connection_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("instagram_connections.id", ondelete="CASCADE"), nullable=False)
    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("direct_conversations.id", ondelete="CASCADE"), nullable=False)
    direct_message_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("direct_messages.id", ondelete="SET NULL"), nullable=True)
    recipient_scoped_id: Mapped[str] = mapped_column(String(180), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(60), nullable=False, default="SEND_MESSAGE")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=MetaMessageOperationStatus.PREPARED.value)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_request_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    messaging_window_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    human_agent_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    manual_reconciliation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    blind_retry_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    safe_request_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    safe_result_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_succeeded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
