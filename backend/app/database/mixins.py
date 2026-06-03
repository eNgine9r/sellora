from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class SoftDeleteMixin:
    """Optional soft-delete columns for future domain entities.

    Domain repositories should treat ``deleted_at is NULL`` as the active-record
    predicate and set ``deleted_by`` to the actor user id when available.
    """

    @declared_attr.directive
    def deleted_at(cls) -> Mapped[datetime | None]:
        return mapped_column(DateTime(timezone=True), nullable=True)

    @declared_attr.directive
    def deleted_by(cls) -> Mapped[UUID | None]:
        return mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class WorkspaceScopedMixin:
    """Required workspace ownership column for future tenant-owned entities."""

    @declared_attr.directive
    def workspace_id(cls) -> Mapped[UUID]:
        return mapped_column(
            PG_UUID(as_uuid=True),
            ForeignKey("workspaces.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        )


# Backward-compatible alias for the original foundation name. New code should
# prefer WorkspaceScopedMixin because it explicitly communicates tenancy scope.
TenantMixin = WorkspaceScopedMixin
