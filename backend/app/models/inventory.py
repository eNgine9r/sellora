from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class Inventory(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "inventory"
    __table_args__ = (
        CheckConstraint("reserved_quantity <= stock_quantity", name="ck_inventory_reserved_lte_stock"),
    )

    product_variant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="CASCADE"), unique=True, nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incoming_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minimum_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    variant = relationship("ProductVariant", back_populates="inventory")
    transactions = relationship("InventoryTransaction", back_populates="inventory")

    @property
    def is_low_stock(self) -> bool:
        return (self.stock_quantity - self.reserved_quantity) <= self.minimum_quantity

    @property
    def available_quantity(self) -> int:
        return self.stock_quantity - self.reserved_quantity
