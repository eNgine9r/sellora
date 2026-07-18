from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import WorkspaceScopedMixin


class OrderFulfillmentOperationState(StrEnum):
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


ACTIVE_FULFILLMENT_OPERATION_STATES = tuple(
    state.value
    for state in (
        OrderFulfillmentOperationState.PENDING,
        OrderFulfillmentOperationState.VALIDATING,
        OrderFulfillmentOperationState.RESERVING_STOCK,
        OrderFulfillmentOperationState.STOCK_RESERVED,
        OrderFulfillmentOperationState.CREATING_SHIPMENT,
        OrderFulfillmentOperationState.SHIPMENT_READY,
        OrderFulfillmentOperationState.PROVIDER_REQUESTING,
        OrderFulfillmentOperationState.PROVIDER_RESULT_RECEIVED,
        OrderFulfillmentOperationState.PERSISTING_RESULT,
        OrderFulfillmentOperationState.RECONCILIATION_REQUIRED,
        OrderFulfillmentOperationState.RECONCILING,
    )
)


class OrderFulfillmentOperationType(StrEnum):
    ORDER_SHIPMENT_TTN = "ORDER_SHIPMENT_TTN"
    LOCAL_SHIPMENT = "LOCAL_SHIPMENT"
    RECONCILIATION = "RECONCILIATION"
    CANCELLATION = "CANCELLATION"


class OrderFulfillmentOperation(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "order_fulfillment_operations"
    __table_args__ = (
        UniqueConstraint("workspace_id", "idempotency_key", name="uq_order_fulfillment_operations_workspace_idempotency_key"),
    )

    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    shipment_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shipments.id", ondelete="SET NULL"), nullable=True)
    nova_poshta_operation_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("nova_poshta_operations.id", ondelete="SET NULL"), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(40), default=OrderFulfillmentOperationType.ORDER_SHIPMENT_TTN.value, nullable=False)
    state: Mapped[str] = mapped_column(String(40), default=OrderFulfillmentOperationState.PENDING.value, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    provider_document_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_document_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reservation_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    shipment_created: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provider_request_started: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provider_result_received: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    local_persistence_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    manual_reconciliation_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blind_retry_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    safe_error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    safe_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
