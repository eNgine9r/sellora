"""Bank/acquiring evidence is a payment *observation*, never automatically sales revenue."""
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import WorkspaceScopedMixin


class BankPaymentRail(StrEnum):
    BANK_IBAN = "BANK_IBAN"
    FOP_CARD = "FOP_CARD"
    MONO_ACQUIRING_LINK = "MONO_ACQUIRING_LINK"
    UNKNOWN_ACCOUNT_TRANSFER = "UNKNOWN_ACCOUNT_TRANSFER"


class BankPaymentKind(StrEnum):
    CUSTOMER_PAYMENT = "CUSTOMER_PAYMENT"
    UNCLASSIFIED_CREDIT = "UNCLASSIFIED_CREDIT"
    ACQUIRING_PAYOUT = "ACQUIRING_PAYOUT"
    REFUND = "REFUND"


class BankPaymentOrigin(StrEnum):
    MANUAL_IMPORT = "MANUAL_IMPORT"
    BANK_API = "BANK_API"
    MERCHANT_API = "MERCHANT_API"


class BankPaymentEvidence(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    """Workspace-isolated evidence; imported manually until authorized bank connection exists.

    A merchant invoice payment and its later settlement/payout are separate
    observations, not two sales. Matching and receipt checks must precede any
    order payment-status transition.
    """

    __tablename__ = "bank_payment_evidence"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "provider", "provider_account_id", "external_reference",
            name="uq_bank_evidence_tenant_provider_account_event",
        ),
        CheckConstraint("amount_minor > 0 AND amount_minor < 100000000000000",
                        name="bank_evidence_positive_minor_amount"),
        CheckConstraint("currency = 'UAH'", name="bank_evidence_ua_currency"),
    )

    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="MONOBANK")
    provider_account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_reference: Mapped[str] = mapped_column(String(160), nullable=False)
    rail: Mapped[str] = mapped_column(String(40), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    origin: Mapped[str] = mapped_column(String(40), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="UAH")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    invoice_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    order_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    candidate_order_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), index=True,
    )
    review_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
    )
