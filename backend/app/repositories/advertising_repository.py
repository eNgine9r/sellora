from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.ad_campaign import AdCampaign
from app.models.ad_metric import AdMetric
from app.models.order import Order


class AdCampaignRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_workspace(self, workspace_id: UUID) -> list[AdCampaign]:
        stmt = select(AdCampaign).where(AdCampaign.workspace_id == workspace_id, AdCampaign.deleted_at.is_(None)).order_by(AdCampaign.created_at.desc())
        return list(self.db.execute(stmt).scalars())

    def get(self, workspace_id: UUID, campaign_id: UUID) -> AdCampaign | None:
        stmt = select(AdCampaign).where(AdCampaign.workspace_id == workspace_id, AdCampaign.id == campaign_id, AdCampaign.deleted_at.is_(None))
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, campaign: AdCampaign) -> AdCampaign:
        self.db.add(campaign)
        self.db.flush()
        return campaign


class AdMetricRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_workspace(self, workspace_id: UUID) -> list[AdMetric]:
        stmt = self._base(workspace_id).order_by(AdMetric.metric_date.desc(), AdMetric.created_at.desc())
        return list(self.db.execute(stmt).scalars())

    def list_for_campaign(self, workspace_id: UUID, campaign_id: UUID) -> list[AdMetric]:
        stmt = self._base(workspace_id).where(AdMetric.campaign_id == campaign_id).order_by(AdMetric.metric_date.desc())
        return list(self.db.execute(stmt).scalars())

    def get(self, workspace_id: UUID, metric_id: UUID) -> AdMetric | None:
        stmt = self._base(workspace_id).where(AdMetric.id == metric_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def find_by_campaign_date(self, workspace_id: UUID, campaign_id: UUID, metric_date: date) -> AdMetric | None:
        stmt = self._base(workspace_id).where(AdMetric.campaign_id == campaign_id, AdMetric.metric_date == metric_date)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, metric: AdMetric) -> AdMetric:
        self.db.add(metric)
        self.db.flush()
        return metric

    def _base(self, workspace_id: UUID) -> Select[tuple[AdMetric]]:
        return select(AdMetric).options(selectinload(AdMetric.campaign)).where(AdMetric.workspace_id == workspace_id, AdMetric.deleted_at.is_(None))


class AdvertisingAnalyticsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_metrics(self, workspace_id: UUID, start_date: date, end_date: date) -> list[AdMetric]:
        stmt = (
            select(AdMetric)
            .options(selectinload(AdMetric.campaign))
            .where(
                AdMetric.workspace_id == workspace_id,
                AdMetric.deleted_at.is_(None),
                AdMetric.metric_date >= start_date,
                AdMetric.metric_date <= end_date,
            )
            .order_by(AdMetric.metric_date.asc())
        )
        return list(self.db.execute(stmt).scalars())

    def group_crm_orders(self, workspace_id: UUID, start: date, end: date) -> list:
        """One row per visible campaign/status/payment; unresolved links stay null.

        Half-open UTC timestamp bounds include the entire selected final date and
        keep the created_at column unwrapped for the existing indexes.
        """
        visible_campaign = and_(
            Order.campaign_id == AdCampaign.id,
            AdCampaign.workspace_id == workspace_id,
            AdCampaign.deleted_at.is_(None),
        )
        stmt = (
            select(
                AdCampaign.id.label("campaign_id"), AdCampaign.name.label("campaign_name"),
                AdCampaign.status.label("campaign_status"), Order.status, Order.payment_status,
                func.count(Order.id).label("orders"), func.sum(Order.revenue).label("revenue"),
            )
            .select_from(Order).outerjoin(AdCampaign, visible_campaign)
            .where(
                Order.workspace_id == workspace_id, Order.deleted_at.is_(None),
                Order.created_at >= datetime.combine(start, time.min, tzinfo=UTC),
                Order.created_at < datetime.combine(end + timedelta(days=1), time.min, tzinfo=UTC),
            )
            .group_by(AdCampaign.id, AdCampaign.name, AdCampaign.status, Order.status, Order.payment_status)
        )
        return list(self.db.execute(stmt).mappings())

    def group_visible_metrics(self, workspace_id: UUID, start: date, end: date) -> list:
        # Aggregate independently: never join metrics to orders or order items.
        stmt = (
            select(
                AdCampaign.id.label("campaign_id"), AdCampaign.name.label("campaign_name"),
                AdCampaign.status.label("campaign_status"),
                func.sum(AdMetric.spend).label("spend"),
                func.sum(AdMetric.orders).label("declared_orders"),
                func.sum(AdMetric.revenue).label("declared_revenue"),
            )
            .select_from(AdMetric).join(AdCampaign, and_(
                AdMetric.campaign_id == AdCampaign.id,
                AdCampaign.workspace_id == workspace_id,
                AdCampaign.deleted_at.is_(None),
            ))
            .where(
                AdMetric.workspace_id == workspace_id, AdMetric.deleted_at.is_(None),
                AdMetric.metric_date >= start, AdMetric.metric_date <= end,
            )
            .group_by(AdCampaign.id, AdCampaign.name, AdCampaign.status)
        )
        return list(self.db.execute(stmt).mappings())
