from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.ad_metric import AdMetric
from app.models.finance_adjustment import FinanceAdjustment
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

    def list_adjustments_for_period(self, workspace_id: UUID, start_at: datetime, end_at: datetime) -> list[FinanceAdjustment]:
        stmt = self._adjustments_base(workspace_id).where(FinanceAdjustment.occurred_at >= start_at, FinanceAdjustment.occurred_at <= end_at)
        return list(self.db.execute(stmt.order_by(FinanceAdjustment.occurred_at.desc())).scalars())

    def list_adjustments(
        self,
        workspace_id: UUID,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        adjustment_type: str | None = None,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[FinanceAdjustment], int]:
        stmt = self._filtered_adjustments(workspace_id, start_at, end_at, adjustment_type, category)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int(self.db.execute(count_stmt).scalar_one() or 0)
        rows = list(self.db.execute(stmt.order_by(FinanceAdjustment.occurred_at.desc(), FinanceAdjustment.created_at.desc()).limit(limit).offset(offset)).scalars())
        return rows, total

    def get_adjustment(self, workspace_id: UUID, adjustment_id: UUID) -> FinanceAdjustment | None:
        stmt = self._adjustments_base(workspace_id).where(FinanceAdjustment.id == adjustment_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def create_adjustment(self, adjustment: FinanceAdjustment) -> FinanceAdjustment:
        self.db.add(adjustment)
        self.db.flush()
        return adjustment

    def order_exists(self, workspace_id: UUID, order_id: UUID) -> bool:
        stmt = select(Order.id).where(
            Order.workspace_id == workspace_id,
            Order.id == order_id,
            Order.deleted_at.is_(None),
        )
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def _adjustments_base(self, workspace_id: UUID) -> Select[tuple[FinanceAdjustment]]:
        return select(FinanceAdjustment).where(FinanceAdjustment.workspace_id == workspace_id, FinanceAdjustment.deleted_at.is_(None))

    def _filtered_adjustments(
        self,
        workspace_id: UUID,
        start_at: datetime | None,
        end_at: datetime | None,
        adjustment_type: str | None,
        category: str | None,
    ) -> Select[tuple[FinanceAdjustment]]:
        stmt = self._adjustments_base(workspace_id)
        if start_at is not None:
            stmt = stmt.where(FinanceAdjustment.occurred_at >= start_at)
        if end_at is not None:
            stmt = stmt.where(FinanceAdjustment.occurred_at <= end_at)
        if adjustment_type:
            stmt = stmt.where(FinanceAdjustment.type == adjustment_type)
        if category:
            stmt = stmt.where(FinanceAdjustment.category == category)
        return stmt
