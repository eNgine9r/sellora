from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class ShipmentCarrier(StrEnum):
    NOVA_POSHTA = "NOVA_POSHTA"
    UKRPOSHTA = "UKRPOSHTA"
    MEEST = "MEEST"
    ROZETKA_DELIVERY = "ROZETKA_DELIVERY"
    OTHER = "OTHER"


class ShipmentStatus(StrEnum):
    DRAFT = "DRAFT"
    CREATED = "CREATED"
    IN_TRANSIT = "IN_TRANSIT"
    ARRIVED = "ARRIVED"
    DELIVERED = "DELIVERED"
    RETURNED = "RETURNED"
    CANCELLED = "CANCELLED"


class Shipment(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "shipments"

    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    customer_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), index=True, nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    carrier: Mapped[str] = mapped_column(String(40), default=ShipmentCarrier.NOVA_POSHTA.value, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default=ShipmentStatus.DRAFT.value, nullable=False)
    recipient_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recipient_phone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    warehouse: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shipping_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    cod_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    declared_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_provider: Mapped[str | None] = mapped_column(String(60), nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    external_status: Mapped[str | None] = mapped_column(String(120), nullable=True)
    nova_poshta_city_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    nova_poshta_warehouse_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    nova_poshta_document_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    nova_poshta_document_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    nova_poshta_raw_status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nova_poshta_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nova_poshta_create_state: Mapped[str | None] = mapped_column(String(40), nullable=True)
    nova_poshta_manual_reconciliation_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    nova_poshta_last_error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

    order = relationship("Order")
    customer = relationship("Customer")
