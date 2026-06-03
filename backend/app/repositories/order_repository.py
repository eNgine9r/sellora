from __future__ import annotations

from datetime import UTC, datetime, time
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order_status_history import OrderStatusHistory


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_workspace(self, workspace_id: UUID, status: str | None = None) -> list[Order]:
        stmt: Select[tuple[Order]] = select(Order).where(Order.workspace_id == workspace_id, Order.deleted_at.is_(None)).options(selectinload(Order.items), selectinload(Order.status_history))
        if status:
            stmt = stmt.where(Order.status == status)
        return list(self.db.execute(stmt.order_by(Order.created_at.desc())).scalars())

    def get(self, workspace_id: UUID, order_id: UUID) -> Order | None:
        stmt = select(Order).where(Order.workspace_id == workspace_id, Order.id == order_id, Order.deleted_at.is_(None)).options(selectinload(Order.items), selectinload(Order.status_history))
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, order: Order) -> Order:
        self.db.add(order)
        self.db.flush()
        return order

    def add_item(self, item: OrderItem) -> OrderItem:
        self.db.add(item)
        self.db.flush()
        return item

    def add_status_history(self, history: OrderStatusHistory) -> OrderStatusHistory:
        self.db.add(history)
        self.db.flush()
        return history

    def next_sequence_for_year(self, workspace_id: UUID, year: int) -> int:
        prefix = f"ORD-{year}-"
        stmt = select(func.count()).select_from(Order).where(Order.workspace_id == workspace_id, Order.order_number.like(f"{prefix}%"))
        return int(self.db.execute(stmt).scalar_one()) + 1

    def dashboard_today(self, workspace_id: UUID) -> tuple[int, object, object]:
        start = datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)
        stmt = select(func.count(Order.id), func.coalesce(func.sum(Order.revenue), 0), func.coalesce(func.sum(Order.net_profit), 0)).where(
            Order.workspace_id == workspace_id,
            Order.deleted_at.is_(None),
            Order.created_at >= start,
        )
        return self.db.execute(stmt).one()
