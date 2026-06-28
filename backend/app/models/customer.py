from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class Customer(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    instagram_username: Mapped[str | None] = mapped_column(String(120), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_spent: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    last_order_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer_tags = relationship("CustomerTag", back_populates="customer", cascade="all, delete-orphan")
    notes = relationship("CustomerNote", back_populates="customer", cascade="all, delete-orphan")
    addresses = relationship("CustomerAddress", back_populates="customer", cascade="all, delete-orphan")
