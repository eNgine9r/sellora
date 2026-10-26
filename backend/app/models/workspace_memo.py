"""Workspace-scoped operational notes and tasks shared by the store team."""
from datetime import date
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class WorkspaceMemo(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "workspace_memos"
    __table_args__ = (
        CheckConstraint("kind IN ('NOTE', 'TASK')", name="kind"),
        Index("ix_workspace_memos_active_due", "workspace_id", "due_on"),
        CheckConstraint("kind = 'TASK' OR (due_on IS NULL AND is_done = false)", name="note_task_fields"),
    )

    kind: Mapped[str] = mapped_column(String(8), nullable=False, default="NOTE")
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    due_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
