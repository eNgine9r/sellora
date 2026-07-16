from uuid import UUID

from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class DeliveryProvider(StrEnum):
    NOVA_POSHTA = "NOVA_POSHTA"
    UKRPOSHTA = "UKRPOSHTA"
    MEEST = "MEEST"
    ROZETKA_DELIVERY = "ROZETKA_DELIVERY"
    OTHER = "OTHER"


class CustomerAddress(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "customer_addresses"
    __table_args__ = (
        Index(
            "uq_customer_addresses_one_active_default",
            "workspace_id",
            "customer_id",
            unique=True,
            postgresql_where=text("is_default = true AND deleted_at IS NULL"),
        ),
    )

    customer_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recipient_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivery_provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    nova_poshta_city_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    nova_poshta_warehouse_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    warehouse_number: Mapped[str | None] = mapped_column(String(40), nullable=True)

    customer = relationship("Customer", back_populates="addresses")
