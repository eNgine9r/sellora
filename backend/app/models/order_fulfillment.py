from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import WorkspaceScopedMixin


class OrderFulfillmentState(StrEnum):
    PREPARED = "PREPARED"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    SHIPMENT_CREATED = "SHIPMENT_CREATED"
    COMPLETED = "COMPLETED"


class OrderFulfillmentResultCode(StrEnum):
    ORDER_AND_TTN_CREATED = "ORDER_AND_TTN_CREATED"
    ORDER_CREATED_TTN_PENDING = "ORDER_CREATED_TTN_PENDING"
    ORDER_CREATED_PROVIDER_RECONCILIATION_REQUIRED = "ORDER_CREATED_PROVIDER_RECONCILIATION_REQUIRED"


class OrderFulfillment(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "order_fulfillments"
    __table_args__ = (
        UniqueConstraint("workspace_id", "idempotency_key", name="uq_order_fulfillments_workspace_idempotency_key"),
    )

    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(40), default=OrderFulfillmentState.PREPARED.value, nullable=False)
    result_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    customer_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    address_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customer_addresses.id", ondelete="SET NULL"), nullable=True)
    order_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    shipment_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shipments.id", ondelete="SET NULL"), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
