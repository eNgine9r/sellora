from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.ad_metric import AdMetric
from app.models.order import Order
from app.models.shipment import Shipment


class FinanceRepository:
    """Read-only finance data access with mandatory workspace scoping."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_orders(self, workspace_id: UUID, start_at: datetime, end_at: datetime) -> list[Order]:
        metric_date = func.coalesce(Order.completed_at, Order.created_at)
        stmt = (
            select(Order)
            .where(
                Order.workspace_id == workspace_id,
                Order.deleted_at.is_(None),
                metric_date >= start_at,
                metric_date <= end_at,
            )
            .options(selectinload(Order.items))
        )
        return list(self.db.execute(stmt).scalars())

    def list_shipments(self, workspace_id: UUID, start_at: datetime, end_at: datetime) -> list[Shipment]:
        stmt = select(Shipment).where(
            Shipment.workspace_id == workspace_id,
            Shipment.deleted_at.is_(None),
            Shipment.created_at >= start_at,
            Shipment.created_at <= end_at,
        )
        return list(self.db.execute(stmt).scalars())

    def list_manual_ad_metrics(self, workspace_id: UUID, start_at: datetime, end_at: datetime) -> Sequence[AdMetric]:
        stmt: Select[tuple[AdMetric]] = select(AdMetric).where(
            AdMetric.workspace_id == workspace_id,
            AdMetric.deleted_at.is_(None),
            AdMetric.metric_date >= start_at.date(),
            AdMetric.metric_date <= end_at.date(),
            or_(AdMetric.source_type.is_(None), AdMetric.source_type.in_(["manual", "csv_import"])),
            or_(AdMetric.external_source.is_(None), AdMetric.external_source != "meta_ads"),
        )
        return list(self.db.execute(stmt).scalars())
