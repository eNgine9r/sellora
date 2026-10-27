from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import WorkspaceScopedMixin


class CodEvidenceSource(StrEnum):
    NOVAPAY_REGISTER = "NOVAPAY_REGISTER"
    BANK_STATEMENT = "BANK_STATEMENT"


class CodEvidenceStatus(StrEnum):
    MATCHED = "MATCHED"
    REVIEW = "REVIEW"


class CodPaymentEvidence(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    """Imported payment evidence, separate from order revenue and cost snapshots."""

    __tablename__ = "cod_payment_evidence"
    __table_args__ = (
        UniqueConstraint("workspace_id", "source", "external_reference",
                         name="uq_cod_evidence_workspace_source_ref"),
        CheckConstraint("gross_amount > 0", name="positive_amount"),
        CheckConstraint("fee_amount >= 0 AND fee_amount <= gross_amount", name="valid_fee"),
    )

    source: Mapped[str] = mapped_column(String(30), nullable=False)
    external_reference: Mapped[str] = mapped_column(String(160), nullable=False)
    tracking_number: Mapped[str | None] = mapped_column(String(40), index=True)
    order_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), index=True)
    shipment_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shipments.id", ondelete="SET NULL"))
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    review_reason: Mapped[str | None] = mapped_column(String(90))
    created_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
