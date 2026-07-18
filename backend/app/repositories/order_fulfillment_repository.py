from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order_fulfillment import ACTIVE_FULFILLMENT_STATES, OrderFulfillment


class OrderFulfillmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_key(self, workspace_id: UUID, idempotency_key: str, *, for_update: bool = False) -> OrderFulfillment | None:
        stmt = select(OrderFulfillment).where(
            OrderFulfillment.workspace_id == workspace_id,
            OrderFulfillment.idempotency_key == idempotency_key,
        )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_latest_for_order(self, workspace_id: UUID, order_id: UUID) -> OrderFulfillment | None:
        stmt = (
            select(OrderFulfillment)
            .where(OrderFulfillment.workspace_id == workspace_id, OrderFulfillment.order_id == order_id)
            .order_by(OrderFulfillment.created_at.desc())
        )
        return self.db.execute(stmt).scalars().first()

    def get_active_for_order(self, workspace_id: UUID, order_id: UUID, *, for_update: bool = False) -> OrderFulfillment | None:
        stmt = select(OrderFulfillment).where(
            OrderFulfillment.workspace_id == workspace_id,
            OrderFulfillment.order_id == order_id,
            OrderFulfillment.state.in_(ACTIVE_FULFILLMENT_STATES),
        )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_completed_by_fingerprint(self, workspace_id: UUID, order_id: UUID, fingerprint: str) -> OrderFulfillment | None:
        stmt = select(OrderFulfillment).where(
            OrderFulfillment.workspace_id == workspace_id,
            OrderFulfillment.order_id == order_id,
            OrderFulfillment.request_fingerprint == fingerprint,
            OrderFulfillment.state == "COMPLETED",
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, operation: OrderFulfillment) -> OrderFulfillment:
        self.db.add(operation)
        self.db.flush()
        return operation
