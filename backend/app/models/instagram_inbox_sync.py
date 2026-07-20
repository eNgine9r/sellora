from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import WorkspaceScopedMixin


class InstagramHistorySyncStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    RETRY_PENDING = "RETRY_PENDING"
    FAILED_SAFE = "FAILED_SAFE"


class InstagramHistorySync(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "instagram_history_syncs"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            name="uq_instagram_history_syncs_workspace",
        ),
    )

    instagram_connection_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("instagram_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=InstagramHistorySyncStatus.PENDING.value,
    )
    requested_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    conversation_cursor: Mapped[str | None] = mapped_column(Text, nullable=True)
    conversation_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    messages_per_conversation: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    conversation_pages_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversations_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversations_synced: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    messages_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    messages_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    messages_existing: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    messages_unavailable: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rate_limit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InstagramMessageState(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "instagram_message_states"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "direct_message_id",
            name="uq_instagram_message_states_workspace_message",
        ),
        UniqueConstraint(
            "workspace_id",
            "provider_message_id",
            name="uq_instagram_message_states_workspace_provider_message",
        ),
    )

    direct_message_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("direct_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_message_id: Mapped[str] = mapped_column(String(180), nullable=False)
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    edit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reaction: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reaction_actor_scoped_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    reaction_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
