from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import WorkspaceScopedMixin


class InstagramParticipantProfileStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    RETRY_PENDING = "RETRY_PENDING"
    UNAVAILABLE = "UNAVAILABLE"


class InstagramParticipantProfile(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "instagram_participant_profiles"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "conversation_id",
            name="uq_instagram_participant_profiles_workspace_conversation",
        ),
        UniqueConstraint(
            "workspace_id",
            "instagram_connection_id",
            "participant_scoped_id",
            name="uq_instagram_participant_profiles_workspace_participant",
        ),
    )

    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("direct_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    instagram_connection_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("instagram_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_scoped_id: Mapped[str] = mapped_column(String(180), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(160))
    profile_picture_url: Mapped[str | None] = mapped_column(Text)
    profile_picture_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    follower_count: Mapped[int | None] = mapped_column(Integer)
    is_verified_user: Mapped[bool | None] = mapped_column(Boolean)
    is_user_follow_business: Mapped[bool | None] = mapped_column(Boolean)
    is_business_follow_user: Mapped[bool | None] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=InstagramParticipantProfileStatus.PENDING.value,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(120))
    last_error_message: Mapped[str | None] = mapped_column(Text)
