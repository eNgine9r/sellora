from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import WorkspaceScopedMixin


class OrderFulfillmentState(StrEnum):
    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    RESERVING_STOCK = "RESERVING_STOCK"
    STOCK_RESERVED = "STOCK_RESERVED"
    CREATING_SHIPMENT = "CREATING_SHIPMENT"
    SHIPMENT_READY = "SHIPMENT_READY"
    PROVIDER_REQUESTING = "PROVIDER_REQUESTING"
    PROVIDER_RESULT_RECEIVED = "PROVIDER_RESULT_RECEIVED"
    PERSISTING_RESULT = "PERSISTING_RESULT"
    COMPLETED = "COMPLETED"
    FAILED_SAFE = "FAILED_SAFE"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    RECONCILING = "RECONCILING"
    CANCELLED = "CANCELLED"


ACTIVE_FULFILLMENT_STATES = tuple(
    state.value
    for state in (
        OrderFulfillmentState.PENDING,
        OrderFulfillmentState.VALIDATING,
        OrderFulfillmentState.RESERVING_STOCK,
        OrderFulfillmentState.STOCK_RESERVED,
        OrderFulfillmentState.CREATING_SHIPMENT,
        OrderFulfillmentState.SHIPMENT_READY,
        OrderFulfillmentState.PROVIDER_REQUESTING,
        OrderFulfillmentState.PROVIDER_RESULT_RECEIVED,
        OrderFulfillmentState.PERSISTING_RESULT,
        OrderFulfillmentState.RECONCILIATION_REQUIRED,
        OrderFulfillmentState.RECONCILING,
    )
)


class OrderFulfillmentOperationType(StrEnum):
    ORDER_SHIPMENT_TTN = "ORDER_SHIPMENT_TTN"
    LOCAL_SHIPMENT = "LOCAL_SHIPMENT"
    RECONCILIATION = "RECONCILIATION"
    CANCELLATION = "CANCELLATION"


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
    state: Mapped[str] = mapped_column(String(40), default=OrderFulfillmentState.PENDING.value, nullable=False)
    result_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    customer_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    address_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customer_addresses.id", ondelete="SET NULL"), nullable=True)
    order_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    shipment_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shipments.id", ondelete="SET NULL"), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    operation_type: Mapped[str] = mapped_column(String(40), default=OrderFulfillmentOperationType.ORDER_SHIPMENT_TTN.value, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    provider_document_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_document_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    nova_poshta_operation_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("nova_poshta_operations.id", ondelete="SET NULL"), nullable=True)
    reservation_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reservation_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    shipment_created: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provider_request_started: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provider_result_received: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    local_persistence_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    manual_reconciliation_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blind_retry_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
