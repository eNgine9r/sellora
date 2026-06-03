from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models.ad_campaign import AdCampaign
from app.models.ad_metric import AdMetric


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
