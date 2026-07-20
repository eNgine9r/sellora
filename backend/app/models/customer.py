from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class CustomerSource(StrEnum):
    MANUAL = "MANUAL"
    INSTAGRAM_DIRECT = "INSTAGRAM_DIRECT"
    IMPORT = "IMPORT"


class CustomerLifecycleStatus(StrEnum):
    PROSPECT = "PROSPECT"
    CUSTOMER = "CUSTOMER"


class CustomerProfileStatus(StrEnum):
    INCOMPLETE = "INCOMPLETE"
    COMPLETE = "COMPLETE"


class Customer(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (
        Index(
            "uq_customers_workspace_instagram_scoped_id_active",
            "workspace_id",
            "instagram_scoped_id",
            unique=True,
            postgresql_where=text("instagram_scoped_id IS NOT NULL AND deleted_at IS NULL"),
        ),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    instagram_username: Mapped[str | None] = mapped_column(String(120), nullable=True)
    instagram_scoped_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default=CustomerSource.MANUAL.value)
    lifecycle_status: Mapped[str] = mapped_column(String(30), nullable=False, default=CustomerLifecycleStatus.CUSTOMER.value)
    profile_status: Mapped[str] = mapped_column(String(30), nullable=False, default=CustomerProfileStatus.INCOMPLETE.value)
    source_direct_conversation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("direct_conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_spent: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    last_order_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer_tags = relationship("CustomerTag", back_populates="customer", cascade="all, delete-orphan")
    notes = relationship("CustomerNote", back_populates="customer", cascade="all, delete-orphan")
    addresses = relationship("CustomerAddress", back_populates="customer", cascade="all, delete-orphan")
