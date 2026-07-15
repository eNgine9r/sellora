from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import WorkspaceScopedMixin


class NovaPoshtaOperationType(StrEnum):
    CREATE_TTN = "CREATE_TTN"


class NovaPoshtaOperationState(StrEnum):
    PREPARED = "PREPARED"
    CALLING_PROVIDER = "CALLING_PROVIDER"
    PROVIDER_ACCEPTED = "PROVIDER_ACCEPTED"
    COMPLETED = "COMPLETED"
    FAILED_SAFE = "FAILED_SAFE"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


class NovaPoshtaOperation(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "nova_poshta_operations"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "shipment_id",
            "operation_type",
            name="uq_nova_poshta_operations_workspace_shipment_type",
        ),
        UniqueConstraint("idempotency_key", name="uq_nova_poshta_operations_idempotency_key"),
        Index("ix_nova_poshta_operations_workspace_state", "workspace_id", "state"),
    )

    shipment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("shipments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    operation_type: Mapped[str] = mapped_column(
        String(40), default=NovaPoshtaOperationType.CREATE_TTN.value, nullable=False
    )
    state: Mapped[str] = mapped_column(
        String(40), default=NovaPoshtaOperationState.PREPARED.value, nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_marker: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_document_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_document_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    provider_called_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    shipment = relationship("Shipment")
