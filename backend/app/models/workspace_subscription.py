"""Current workspace subscription term; payment processing is a separate concern."""
from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SubscriptionStatus(str, Enum):
    PENDING = "PENDING"
    TRIALING = "TRIALING"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class WorkspaceSubscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workspace_subscriptions"
    __table_args__ = (
        UniqueConstraint("workspace_id", name="uq_workspace_subscriptions_workspace_id"),
        CheckConstraint("status IN ('PENDING','TRIALING','ACTIVE','PAST_DUE','CANCELED','EXPIRED')", name="subscription_status"),
        CheckConstraint("current_period_end > current_period_start", name="subscription_period"),
        CheckConstraint("length(trim(plan_code)) > 0", name="subscription_plan_code"),
        CheckConstraint("NOT cancel_at_period_end OR status IN ('ACTIVE','TRIALING')", name="subscription_cancel_at_end"),
    )

    # The unique constraint also supplies the workspace lookup/FK index.
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    plan_code: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
