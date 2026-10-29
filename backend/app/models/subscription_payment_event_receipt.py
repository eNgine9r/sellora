"""Append-only provider event evidence; never a subscription entitlement."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class SubscriptionPaymentEventReceipt(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "subscription_payment_event_receipts"
    __table_args__ = (
        # A provider identity cannot be replayed into a different workspace.
        UniqueConstraint("provider", "provider_account_id", "external_event_id",
                         name="uq_subscription_payment_receipt_provider_event"),
        CheckConstraint("amount >= 0 AND amount < 100000000000000", name="receipt_amount"),
        CheckConstraint("length(currency) = 3 AND currency = upper(currency)", name="receipt_currency"),
        CheckConstraint("length(fingerprint) = 64", name="receipt_fingerprint"),
        CheckConstraint("length(trim(provider)) > 0 AND provider = lower(provider)", name="receipt_provider"),
        CheckConstraint("length(trim(provider_account_id)) > 0", name="receipt_provider_account"),
        CheckConstraint("length(trim(external_event_id)) > 0", name="receipt_event_id"),
        CheckConstraint("length(trim(transaction_id)) > 0", name="receipt_transaction_id"),
        CheckConstraint("length(trim(event_type)) > 0", name="receipt_event_type"),
    )

    # Evidence survives workspace deactivation and prevents destructive hard deletion.
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_event_id: Mapped[str] = mapped_column(String(160), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(160), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
