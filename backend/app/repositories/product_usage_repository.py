from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select, text, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.product import Product
from app.models.product_usage import DROPPED_EVENTS, ProductUsageDaily, ProductUsageEvent, UsageEvent, UsageSource


class ProductUsageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self, workspace_id: UUID, event: UsageEvent, source: UsageSource, source_key: str, occurred_at: datetime,
    ) -> None:
        statement = insert(ProductUsageEvent).values(
            id=uuid4(), workspace_id=workspace_id, event_type=event, source=source,
            source_key=source_key, occurred_at=occurred_at,
        ).on_conflict_do_nothing(
            index_elements=["workspace_id", "event_type", "source_key"],
        ).returning(ProductUsageEvent.id)
        if self.db.scalar(statement) is not None:
            self.increment_daily(workspace_id, occurred_at.date(), event)

    def increment_daily(self, workspace_id: UUID, day: date, event: str) -> None:
        statement = insert(ProductUsageDaily).values(
            workspace_id=workspace_id, day=day, event_type=event, event_count=1,
        ).on_conflict_do_update(
            index_elements=["workspace_id", "day", "event_type"],
            set_={"event_count": ProductUsageDaily.event_count + 1},
        )
        self.db.execute(statement)

    def other_product_exists(self, workspace_id: UUID, product_id: UUID) -> bool:
        return bool(self.db.scalar(select(select(Product.id).where(
            Product.workspace_id == workspace_id, Product.id != product_id,
        ).exists())))

    def other_order_exists(self, workspace_id: UUID, order_id: UUID) -> bool:
        return bool(self.db.scalar(select(select(Order.id).where(
            Order.workspace_id == workspace_id, Order.id != order_id, Order.is_historical.is_(False),
        ).exists())))

    def set_capture_lock_timeout(self) -> str:
        previous = self.db.execute(text("SHOW lock_timeout")).scalar_one()
        self.db.execute(text("SET LOCAL lock_timeout = '150ms'"))
        return previous

    def restore_lock_timeout(self, previous: str) -> None:
        self.db.execute(text("SELECT set_config('lock_timeout', :previous, true)"), {"previous": previous})

    def totals(self, first_day: date, last_day: date, workspace_id: UUID | None):
        daily = ProductUsageDaily
        real_events = daily.event_type != DROPPED_EVENTS

        def total(event: str):
            return func.coalesce(func.sum(daily.event_count).filter(daily.event_type == event), 0)

        statement = select(
            func.count(daily.workspace_id.distinct()).filter(real_events).label("active_workspaces"),
            func.count(func.distinct(tuple_(daily.workspace_id, daily.day))).filter(real_events).label("active_workspace_days"),
            total(UsageEvent.WORKSPACE_ACTIVATED).label("activated_workspaces"),
            total(UsageEvent.FIRST_PRODUCT).label("first_products"),
            total(UsageEvent.FIRST_ORDER).label("first_orders"),
            total(UsageEvent.ORDER_CREATED).label("orders_created"),
            total(UsageEvent.INTEGRATION_USED).label("integration_days"),
            total(DROPPED_EVENTS).label("dropped_operations"),
        ).where(and_(daily.day >= first_day, daily.day <= last_day))
        if workspace_id is not None:
            statement = statement.where(daily.workspace_id == workspace_id)
        return self.db.execute(statement).mappings().one()
