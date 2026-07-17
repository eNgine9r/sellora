from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order_fulfillment import OrderFulfillment


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

    def create(self, operation: OrderFulfillment) -> OrderFulfillment:
        self.db.add(operation)
        self.db.flush()
        return operation
