from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class DirectChannel(StrEnum):
    SYNTHETIC = "SYNTHETIC"
    INSTAGRAM = "INSTAGRAM"
    MANUAL = "MANUAL"


class DirectConversationStatus(StrEnum):
    OPEN = "OPEN"
    WAITING_FOR_CUSTOMER = "WAITING_FOR_CUSTOMER"
    WAITING_FOR_MANAGER = "WAITING_FOR_MANAGER"
    RESOLVED = "RESOLVED"
    ARCHIVED = "ARCHIVED"
    SPAM = "SPAM"


class AIPriority(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class DirectAIProcessingStatus(StrEnum):
    NOT_REQUESTED = "NOT_REQUESTED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class DirectMessageDirection(StrEnum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"
    INTERNAL = "INTERNAL"


class DirectMessageSenderType(StrEnum):
    CUSTOMER = "CUSTOMER"
    MANAGER = "MANAGER"
    SYSTEM = "SYSTEM"
    AI_DRAFT = "AI_DRAFT"


class DirectMessageType(StrEnum):
    TEXT = "TEXT"
    IMAGE_PLACEHOLDER = "IMAGE_PLACEHOLDER"
    VOICE_PLACEHOLDER = "VOICE_PLACEHOLDER"
    SYSTEM_EVENT = "SYSTEM_EVENT"


class DirectMessageProcessingStatus(StrEnum):
    RECEIVED = "RECEIVED"
    ANALYZABLE = "ANALYZABLE"
    IGNORED = "IGNORED"
    FAILED = "FAILED"


class AIIntent(StrEnum):
    PRODUCT_INQUIRY = "PRODUCT_INQUIRY"
    PRICE_INQUIRY = "PRICE_INQUIRY"
    AVAILABILITY_CHECK = "AVAILABILITY_CHECK"
    ORDER_REQUEST = "ORDER_REQUEST"
    DELIVERY_QUESTION = "DELIVERY_QUESTION"
    PAYMENT_QUESTION = "PAYMENT_QUESTION"
    ORDER_STATUS = "ORDER_STATUS"
    RETURN_REQUEST = "RETURN_REQUEST"
    EXCHANGE_REQUEST = "EXCHANGE_REQUEST"
    COMPLAINT = "COMPLAINT"
    DISCOUNT_REQUEST = "DISCOUNT_REQUEST"
    GENERAL_MESSAGE = "GENERAL_MESSAGE"
    THANK_YOU = "THANK_YOU"
    SPAM = "SPAM"
    UNKNOWN = "UNKNOWN"


class AISentiment(StrEnum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"
    ANGRY = "ANGRY"
    UNKNOWN = "UNKNOWN"


class AIAnalysisStatus(StrEnum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED_SAFE = "FAILED_SAFE"
    RATE_LIMITED = "RATE_LIMITED"
    BUDGET_BLOCKED = "BUDGET_BLOCKED"
    CANCELLED = "CANCELLED"


class AISuggestionStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class AISuggestionType(StrEnum):
    REPLY_DRAFT = "REPLY_DRAFT"
    CLARIFICATION_DRAFT = "CLARIFICATION_DRAFT"
    CREATE_LEAD = "CREATE_LEAD"
    LINK_LEAD = "LINK_LEAD"
    CREATE_CUSTOMER = "CREATE_CUSTOMER"
    LINK_CUSTOMER = "LINK_CUSTOMER"
    CREATE_ORDER_DRAFT = "CREATE_ORDER_DRAFT"
    UPDATE_CONVERSATION = "UPDATE_CONVERSATION"
    ESCALATE_TO_MANAGER = "ESCALATE_TO_MANAGER"
    MARK_AS_SPAM = "MARK_AS_SPAM"


class AIActionType(StrEnum):
    CREATE_LEAD = "CREATE_LEAD"
    CREATE_CUSTOMER = "CREATE_CUSTOMER"
    CREATE_ORDER_DRAFT = "CREATE_ORDER_DRAFT"
    LINK_CUSTOMER = "LINK_CUSTOMER"
    LINK_LEAD = "LINK_LEAD"
    UPDATE_CONVERSATION = "UPDATE_CONVERSATION"


class AIFeedbackRating(StrEnum):
    HELPFUL = "HELPFUL"
    PARTIALLY_HELPFUL = "PARTIALLY_HELPFUL"
    NOT_HELPFUL = "NOT_HELPFUL"
    INCORRECT = "INCORRECT"


class DirectConversation(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "direct_conversations"

    channel: Mapped[str] = mapped_column(String(30), nullable=False, default=DirectChannel.SYNTHETIC.value)
    external_account_id: Mapped[str | None] = mapped_column(String(160))
    external_conversation_id: Mapped[str | None] = mapped_column(String(160))
    participant_external_id: Mapped[str | None] = mapped_column(String(160))
    participant_username: Mapped[str | None] = mapped_column(String(160))
    participant_display_name: Mapped[str | None] = mapped_column(String(255))
    linked_lead_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"))
    linked_customer_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"))
    linked_order_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=DirectConversationStatus.OPEN.value)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default=AIPriority.NORMAL.value)
    assigned_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    unread_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_inbound_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_outbound_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ai_processing_status: Mapped[str] = mapped_column(String(40), nullable=False, default=DirectAIProcessingStatus.NOT_REQUESTED.value)
    latest_ai_analysis_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    updated_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    instagram_connection_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("instagram_connections.id", ondelete="SET NULL"))
    external_thread_id: Mapped[str | None] = mapped_column(String(180))
    participant_scoped_id: Mapped[str | None] = mapped_column(String(180))
    messaging_window_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    human_agent_window_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_sync_status: Mapped[str | None] = mapped_column(String(40))


class DirectMessage(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "direct_messages"

    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("direct_conversations.id", ondelete="CASCADE"), nullable=False)
    external_message_id: Mapped[str | None] = mapped_column(String(160))
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)
    message_type: Mapped[str] = mapped_column(String(30), nullable=False, default=DirectMessageType.TEXT.value)
    text: Mapped[str | None] = mapped_column(Text)
    safe_text_hash: Mapped[str | None] = mapped_column(String(64))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_status: Mapped[str] = mapped_column(String(30), nullable=False, default=DirectMessageProcessingStatus.RECEIVED.value)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    provider: Mapped[str | None] = mapped_column(String(40))
    provider_message_id: Mapped[str | None] = mapped_column(String(180))
    provider_event_id: Mapped[str | None] = mapped_column(String(180))
    delivery_status: Mapped[str | None] = mapped_column(String(40))
    message_payload_type: Mapped[str | None] = mapped_column(String(40))
    attachment_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    provider_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))


class AIAnalysis(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, Base):
    __tablename__ = "ai_analyses"

    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("direct_conversations.id", ondelete="CASCADE"), nullable=False)
    source_message_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("direct_messages.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_key: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    detected_language: Mapped[str | None] = mapped_column(String(12))
    detected_intent: Mapped[str | None] = mapped_column(String(60))
    intent_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    sentiment: Mapped[str | None] = mapped_column(String(20))
    sentiment_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    urgency: Mapped[str | None] = mapped_column(String(20))
    requires_human: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    clarification_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    structured_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    safe_error_code: Mapped[str | None] = mapped_column(String(120))
    safe_error_message: Mapped[str | None] = mapped_column(Text)
    provider_request_id: Mapped[str | None] = mapped_column(String(160))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Numeric(12, 6))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))


class AISuggestion(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "ai_suggestions"

    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("direct_conversations.id", ondelete="CASCADE"), nullable=False)
    analysis_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("ai_analyses.id", ondelete="CASCADE"), nullable=False)
    suggestion_type: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=AISuggestionStatus.REVIEW_REQUIRED.value)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    draft_text: Mapped[str | None] = mapped_column(Text)
    structured_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    reviewed_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(String(500))
    applied_entity_type: Mapped[str | None] = mapped_column(String(80))
    applied_entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AIActionDraft(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "ai_action_drafts"
    __table_args__ = (UniqueConstraint("workspace_id", "idempotency_key", name="uq_ai_action_drafts_workspace_idempotency_key"),)

    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("direct_conversations.id", ondelete="CASCADE"), nullable=False)
    suggestion_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("ai_suggestions.id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=AISuggestionStatus.DRAFT.value)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    validation_errors: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    validation_warnings: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    approved_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_entity_type: Mapped[str | None] = mapped_column(String(80))
    result_entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)


class AIWorkspaceSettings(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "ai_workspace_settings"
    __table_args__ = (UniqueConstraint("workspace_id", name="uq_ai_workspace_settings_workspace_id"),)

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    synthetic_inbox_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    direct_intelligence_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auto_analysis_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reply_suggestions_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    action_drafts_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    daily_request_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    daily_token_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=100000)
    monthly_budget_usd: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=25)
    max_context_messages: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    max_input_characters: Mapped[int] = mapped_column(Integer, nullable=False, default=12000)
    minimum_action_confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.85)
    minimum_product_match_confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.85)
    updated_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))


class AIUsageEvent(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, Base):
    __tablename__ = "ai_usage_events"

    user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    conversation_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("direct_conversations.id", ondelete="SET NULL"))
    analysis_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("ai_analyses.id", ondelete="SET NULL"))
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    request_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AIFeedback(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, Base):
    __tablename__ = "ai_feedback"

    analysis_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("ai_analyses.id", ondelete="SET NULL"))
    suggestion_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("ai_suggestions.id", ondelete="SET NULL"))
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500))
    corrected_intent: Mapped[str | None] = mapped_column(String(60))
    corrected_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
