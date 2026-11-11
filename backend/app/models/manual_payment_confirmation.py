"""Human-attested bank arrival and Direct receipt checks (no monobank API).

An immutable record of a manager's *manual* claim; NOT bank-provider attestation
and NOT a separately recognizable second sale. Never used as an acquiring payout.
"""
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import WorkspaceScopedMixin


class ManualPaymentMethod(StrEnum):
    BANK_IBAN = "BANK_IBAN"
    FOP_CARD = "FOP_CARD"
    MONO_ACQUIRING_LINK = "MONO_ACQUIRING_LINK"


class ManualPaymentConfirmation(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    """Unique order & transaction reference within each isolated workspace."""

    __tablename__ = "manual_payment_confirmations"
    __table_args__ = (
        UniqueConstraint("workspace_id", "order_id", name="uq_manual_payment_workspace_order"),
        UniqueConstraint("workspace_id", "transaction_reference", name="uq_manual_payment_workspace_transaction"),
        CheckConstraint("amount_minor > 0", name="manual_payment_amount_positive"),
        CheckConstraint("currency = 'UAH'", name="manual_payment_ua_currency"),
        CheckConstraint("receipt_checked IS TRUE AND bank_received_checked IS TRUE",
                        name="manual_payment_both_checks_required"),
    )

    order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True,
    )
    payment_method: Mapped[str] = mapped_column(String(40), nullable=False)
    transaction_reference: Mapped[str] = mapped_column(String(160), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="UAH")
    receipt_checked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    bank_received_checked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Optional optional claim about the Direct receipt; no PII or screenshot retained here.
    receipt_note: Mapped[str | None] = mapped_column(String(240), nullable=True)
    verified_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
