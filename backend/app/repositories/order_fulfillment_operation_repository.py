from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order_fulfillment_operation import ACTIVE_FULFILLMENT_OPERATION_STATES, OrderFulfillmentOperation


class OrderFulfillmentOperationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, workspace_id: UUID, operation_id: UUID, *, for_update: bool = False) -> OrderFulfillmentOperation | None:
        stmt = select(OrderFulfillmentOperation).where(OrderFulfillmentOperation.workspace_id == workspace_id, OrderFulfillmentOperation.id == operation_id)
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_key(self, workspace_id: UUID, idempotency_key: str, *, for_update: bool = False) -> OrderFulfillmentOperation | None:
        stmt = select(OrderFulfillmentOperation).where(OrderFulfillmentOperation.workspace_id == workspace_id, OrderFulfillmentOperation.idempotency_key == idempotency_key)
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_latest_for_order(self, workspace_id: UUID, order_id: UUID) -> OrderFulfillmentOperation | None:
        stmt = (
            select(OrderFulfillmentOperation)
            .where(OrderFulfillmentOperation.workspace_id == workspace_id, OrderFulfillmentOperation.order_id == order_id)
            .order_by(OrderFulfillmentOperation.created_at.desc())
        )
        return self.db.execute(stmt).scalars().first()

    def get_active_for_order(self, workspace_id: UUID, order_id: UUID, *, for_update: bool = False) -> OrderFulfillmentOperation | None:
        stmt = select(OrderFulfillmentOperation).where(
            OrderFulfillmentOperation.workspace_id == workspace_id,
            OrderFulfillmentOperation.order_id == order_id,
            OrderFulfillmentOperation.state.in_(ACTIVE_FULFILLMENT_OPERATION_STATES),
        )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_completed_by_fingerprint(self, workspace_id: UUID, order_id: UUID, fingerprint: str) -> OrderFulfillmentOperation | None:
        stmt = select(OrderFulfillmentOperation).where(
            OrderFulfillmentOperation.workspace_id == workspace_id,
            OrderFulfillmentOperation.order_id == order_id,
            OrderFulfillmentOperation.request_fingerprint == fingerprint,
            OrderFulfillmentOperation.state == "COMPLETED",
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, operation: OrderFulfillmentOperation) -> OrderFulfillmentOperation:
        self.db.add(operation)
        self.db.flush()
        return operation
