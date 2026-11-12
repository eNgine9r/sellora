from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class PlatformRole(StrEnum):
    ADMIN = "PLATFORM_ADMIN"
    SUPPORT = "PLATFORM_SUPPORT"
    AUDITOR = "PLATFORM_AUDITOR"


class PlatformGrant(Base):
    __tablename__ = "platform_operator_grants"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlatformAuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "platform_audit_events"

    actor_user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    actor_role: Mapped[str | None] = mapped_column(String(24))
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    outcome: Mapped[str] = mapped_column(String(12), nullable=False)
    workspace_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    target_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    target_role: Mapped[str | None] = mapped_column(String(24))
    approval_ref: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
