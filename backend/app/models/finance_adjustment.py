from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class FinanceAdjustmentType(StrEnum):
    EXPENSE = "EXPENSE"
    REFUND = "REFUND"
    DISCOUNT = "DISCOUNT"
    FEE = "FEE"
    SHIPPING_ADJUSTMENT = "SHIPPING_ADJUSTMENT"
    CORRECTION = "CORRECTION"
    OTHER = "OTHER"


class FinanceAdjustmentCategory(StrEnum):
    PACKAGING = "PACKAGING"
    DELIVERY = "DELIVERY"
    PAYMENT_FEE = "PAYMENT_FEE"
    MARKETPLACE_FEE = "MARKETPLACE_FEE"
    TOOLS = "TOOLS"
    SALARY = "SALARY"
    RENT = "RENT"
    REFUND = "REFUND"
    DISCOUNT = "DISCOUNT"
    ADJUSTMENT = "ADJUSTMENT"
    OTHER = "OTHER"


class FinanceAdjustmentSource(StrEnum):
    MANUAL = "MANUAL"


class FinanceAdjustment(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "finance_adjustments"

    type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="UAH", nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(40), default=FinanceAdjustmentSource.MANUAL.value, nullable=False)
    created_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    order = relationship("Order")
