from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.ad_campaign import AdCampaign
from app.models.ad_metric import AdMetric


@dataclass(frozen=True)
class ExistingAdCampaignSnapshot:
    id: UUID
    workspace_id: UUID
    name: str
    platform: str
    status: str
    created_at: datetime | None = None
    external_source: str | None = None
    external_account_id: str | None = None
    external_campaign_id: str | None = None
    sync_source: str | None = None


@dataclass(frozen=True)
class ExistingAdMetricSnapshot:
    id: UUID
    workspace_id: UUID
    campaign_id: UUID
    campaign_name: str
    metric_date: date
    spend: Decimal
    impressions: int
    clicks: int
    messages: int
    leads: int
    orders: int
    revenue: Decimal
    net_profit: Decimal
    source_label: str = "manual_or_csv"
    source_type: str | None = None
    external_source: str | None = None
    external_account_id: str | None = None
    external_campaign_id: str | None = None
    sync_run_id: UUID | None = None


class AdvertisingSyncReadRepository(Protocol):
    """Read-only repository boundary for Meta sync previews."""

    def list_campaign_snapshots(self, workspace_id: UUID) -> list[ExistingAdCampaignSnapshot]:
        """Return existing campaign snapshots for one workspace."""

    def list_metric_snapshots(self, workspace_id: UUID, date_from: date, date_to: date) -> list[ExistingAdMetricSnapshot]:
        """Return existing metric snapshots for one workspace and date range."""


class SQLAlchemyAdvertisingSyncReadRepository:
    """SQLAlchemy read-only implementation for sync preview comparison.

    This class intentionally has no create, update, delete, flush, or commit
    methods. It can be replaced by an in-memory test repository.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_campaign_snapshots(self, workspace_id: UUID) -> list[ExistingAdCampaignSnapshot]:
        stmt = (
            select(AdCampaign)
            .where(AdCampaign.workspace_id == workspace_id, AdCampaign.deleted_at.is_(None))
            .order_by(AdCampaign.created_at.desc())
        )
        campaigns = self.db.execute(stmt).scalars()
        return [
            ExistingAdCampaignSnapshot(
                id=campaign.id,
                workspace_id=campaign.workspace_id,
                name=campaign.name,
                platform=campaign.platform,
                status=campaign.status,
                created_at=campaign.created_at,
                external_source=campaign.external_source,
                external_account_id=campaign.external_account_id,
                external_campaign_id=campaign.external_campaign_id,
                sync_source=campaign.sync_source,
            )
            for campaign in campaigns
        ]

    def list_metric_snapshots(self, workspace_id: UUID, date_from: date, date_to: date) -> list[ExistingAdMetricSnapshot]:
        stmt = (
            select(AdMetric)
            .options(selectinload(AdMetric.campaign))
            .where(
                AdMetric.workspace_id == workspace_id,
                AdMetric.deleted_at.is_(None),
                AdMetric.metric_date >= date_from,
                AdMetric.metric_date <= date_to,
            )
            .order_by(AdMetric.metric_date.asc())
        )
        metrics = self.db.execute(stmt).scalars()
        return [
            ExistingAdMetricSnapshot(
                id=metric.id,
                workspace_id=metric.workspace_id,
                campaign_id=metric.campaign_id,
                campaign_name=metric.campaign.name if metric.campaign else "Unknown campaign",
                metric_date=metric.metric_date,
                spend=Decimal(str(metric.spend or 0)).quantize(Decimal("0.01")),
                impressions=int(metric.impressions or 0),
                clicks=int(metric.clicks or 0),
                messages=int(metric.messages or 0),
                leads=int(metric.leads or 0),
                orders=int(metric.orders or 0),
                revenue=Decimal(str(metric.revenue or 0)).quantize(Decimal("0.01")),
                net_profit=Decimal(str(metric.net_profit or 0)).quantize(Decimal("0.01")),
                source_label=metric.source_type or "manual_or_csv",
                source_type=metric.source_type,
                external_source=metric.external_source,
                external_account_id=metric.external_account_id,
                external_campaign_id=metric.external_campaign_id,
                sync_run_id=metric.sync_run_id,
            )
            for metric in metrics
        ]
