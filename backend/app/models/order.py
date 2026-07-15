from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class OrderStatus(StrEnum):
    NEW = "NEW"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    RETURNED = "RETURNED"
    CANCELLED = "CANCELLED"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    COD = "COD"
    REFUNDED = "REFUNDED"


class Order(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("workspace_id", "order_number", name="uq_orders_workspace_id_order_number"),
    )

    order_number: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    customer_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    campaign_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("ad_campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default=OrderStatus.NEW.value, nullable=False)
    payment_status: Mapped[str] = mapped_column(String(30), default=PaymentStatus.PENDING.value, nullable=False)
    is_historical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    product_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    ad_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    cod_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    other_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    net_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    status_history = relationship("OrderStatusHistory", back_populates="order", cascade="all, delete-orphan")
    customer = relationship("Customer")
    campaign = relationship("AdCampaign", back_populates="orders")

    @property
    def customer_name(self) -> str | None:
        return self.customer.name if self.customer else None

    @property
    def customer_phone(self) -> str | None:
        return self.customer.phone if self.customer else None

    @property
    def customer_instagram_username(self) -> str | None:
        return self.customer.instagram_username if self.customer else None

    @property
    def campaign_name(self) -> str | None:
        return self.campaign.name if self.campaign else None
