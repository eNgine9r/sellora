from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class InventoryTransactionType(StrEnum):
    STOCK_IN = "STOCK_IN"
    STOCK_OUT = "STOCK_OUT"
    RESERVE = "RESERVE"
    UNRESERVE = "UNRESERVE"
    RETURN = "RETURN"
    ADJUSTMENT = "ADJUSTMENT"


class InventoryTransaction(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "inventory_transactions"

    inventory_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("inventory.id", ondelete="CASCADE"), nullable=False)
    product_variant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    new_stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_reserved_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    new_reserved_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    inventory = relationship("Inventory", back_populates="transactions")
    variant = relationship("ProductVariant")
