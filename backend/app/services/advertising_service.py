from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.ad_campaign import AdCampaign, AdCampaignStatus
from app.models.ad_metric import AdMetric
from app.repositories.advertising_repository import AdCampaignRepository, AdMetricRepository, AdvertisingAnalyticsRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.advertising import (
    AdCampaignCreate,
    AdCampaignUpdate,
    AdMetricCreate,
    AdMetricResponse,
    AdvertisingSummaryResponse,
    AdvertisingTrendPoint,
    CampaignPerformanceResponse,
)
from app.services.business_utils import snapshot


class AdvertisingServiceError(ValueError):
    pass


class AdCampaignService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.campaigns = AdCampaignRepository(db)
        self.audit_logs = AuditLogRepository(db)

    def list(self, workspace_id: UUID) -> list[AdCampaign]:
        return self.campaigns.list(workspace_id)

    def get(self, workspace_id: UUID, campaign_id: UUID) -> AdCampaign:
        campaign = self.campaigns.get(workspace_id, campaign_id)
        if campaign is None:
            raise AdvertisingServiceError("Advertising campaign not found")
        return campaign

    def create(self, workspace_id: UUID, payload: AdCampaignCreate, actor_user_id: UUID | None) -> AdCampaign:
        campaign = AdCampaign(workspace_id=workspace_id, **payload.model_dump(exclude_none=True))
        if not campaign.status:
            campaign.status = AdCampaignStatus.ACTIVE.value
        self.campaigns.create(campaign)
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="AdCampaign", entity_id=campaign.id, action="AD_CAMPAIGN_CREATE", new_value=snapshot(campaign))
        self.db.commit(); self.db.refresh(campaign); return campaign

    def update(self, workspace_id: UUID, campaign_id: UUID, payload: AdCampaignUpdate, actor_user_id: UUID | None) -> AdCampaign:
        campaign = self.get(workspace_id, campaign_id)
        before = snapshot(campaign)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(campaign, field, value)
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="AdCampaign", entity_id=campaign.id, action="AD_CAMPAIGN_UPDATE", old_value=before, new_value=snapshot(campaign))
        self.db.commit(); self.db.refresh(campaign); return campaign

    def delete(self, workspace_id: UUID, campaign_id: UUID, actor_user_id: UUID | None) -> None:
        campaign = self.get(workspace_id, campaign_id)
        campaign.deleted_at = datetime.now(UTC)
        campaign.deleted_by = actor_user_id
        campaign.status = AdCampaignStatus.ARCHIVED.value
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="AdCampaign", entity_id=campaign.id, action="AD_CAMPAIGN_DELETE", old_value=snapshot(campaign))
        self.db.commit()


class AdMetricService:
    non_negative_fields = ("spend", "impressions", "reach", "clicks", "messages", "leads", "orders", "revenue")

    def __init__(self, db: Session) -> None:
        self.db = db
        self.campaigns = AdCampaignRepository(db)
        self.metrics = AdMetricRepository(db)
        self.audit_logs = AuditLogRepository(db)

    def list(self, workspace_id: UUID, include_sensitive: bool) -> list[AdMetricResponse]:
        return [metric_response(metric, include_sensitive) for metric in self.metrics.list(workspace_id)]

    def list_for_campaign(self, workspace_id: UUID, campaign_id: UUID, include_sensitive: bool) -> list[AdMetricResponse]:
        if self.campaigns.get(workspace_id, campaign_id) is None:
            raise AdvertisingServiceError("Advertising campaign not found")
        return [metric_response(metric, include_sensitive) for metric in self.metrics.list_for_campaign(workspace_id, campaign_id)]

    def create(self, workspace_id: UUID, payload: AdMetricCreate, actor_user_id: UUID | None) -> AdMetricResponse:
        self._validate_payload(workspace_id, payload)
        metric = AdMetric(workspace_id=workspace_id, **payload.model_dump())
        self.metrics.create(metric)
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="AdMetric", entity_id=metric.id, action="AD_METRIC_CREATE", new_value=snapshot(metric))
        self.db.commit(); self.db.refresh(metric); return metric_response(metric, include_sensitive=True)

    def delete(self, workspace_id: UUID, metric_id: UUID, actor_user_id: UUID | None) -> None:
        metric = self.metrics.get(workspace_id, metric_id)
        if metric is None:
            raise AdvertisingServiceError("Advertising metric not found")
        metric.deleted_at = datetime.now(UTC)
        metric.deleted_by = actor_user_id
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="AdMetric", entity_id=metric.id, action="AD_METRIC_DELETE", old_value=snapshot(metric))
        self.db.commit()

    def _validate_payload(self, workspace_id: UUID, payload: AdMetricCreate) -> None:
        if self.campaigns.get(workspace_id, payload.campaign_id) is None:
            raise AdvertisingServiceError("Advertising campaign not found in workspace")
        if self.metrics.find_by_campaign_date(workspace_id, payload.campaign_id, payload.metric_date):
            raise AdvertisingServiceError("Daily advertising metrics already exist for this campaign and date")
        for field in self.non_negative_fields:
            value = getattr(payload, field)
            if value < 0:
                raise AdvertisingServiceError(f"{field} cannot be negative")


class AdvertisingAnalyticsService:
    def __init__(self, db: Session) -> None:
        self.repository = AdvertisingAnalyticsRepository(db)

    def summary(self, workspace_id: UUID, start_date: date | None, end_date: date | None, include_sensitive: bool) -> AdvertisingSummaryResponse:
        start, end = resolve_date_range(start_date, end_date)
        return summary_from_metrics(self.repository.list_metrics(workspace_id, start, end), include_sensitive)

    def campaign_performance(self, workspace_id: UUID, start_date: date | None, end_date: date | None, limit: int, include_sensitive: bool) -> list[CampaignPerformanceResponse]:
        start, end = resolve_date_range(start_date, end_date)
        grouped: dict[UUID, list[AdMetric]] = defaultdict(list)
        for metric in self.repository.list_metrics(workspace_id, start, end):
            grouped[metric.campaign_id].append(metric)
        rows: list[CampaignPerformanceResponse] = []
        for campaign_id, metrics in grouped.items():
            totals = aggregate(metrics)
            campaign = metrics[0].campaign
            rows.append(CampaignPerformanceResponse(
                campaign_id=campaign_id,
                campaign_name=campaign.name if campaign else "Unknown campaign",
                platform=campaign.platform if campaign else "OTHER",
                status=campaign.status if campaign else "ARCHIVED",
                spend=totals["spend"],
                revenue=totals["revenue"],
                net_profit=totals["net_profit"] if include_sensitive else None,
                orders=totals["orders"],
                leads=totals["leads"],
                messages=totals["messages"],
                cpa=safe_div(totals["spend"], totals["orders"]),
                cpl=safe_div(totals["spend"], totals["leads"]),
                roas=safe_div(totals["revenue"], totals["spend"]),
                roi=percent_div(totals["net_profit"], totals["spend"]) if include_sensitive else None,
            ))
        return sorted(rows, key=lambda row: row.spend, reverse=True)[:limit]

    def trend(self, workspace_id: UUID, start_date: date | None, end_date: date | None, include_sensitive: bool) -> list[AdvertisingTrendPoint]:
        start, end = resolve_date_range(start_date, end_date)
        grouped: dict[date, list[AdMetric]] = defaultdict(list)
        for metric in self.repository.list_metrics(workspace_id, start, end):
            grouped[metric.metric_date].append(metric)
        return [
            AdvertisingTrendPoint(
                date=metric_date,
                spend=(totals := aggregate(metrics))["spend"],
                revenue=totals["revenue"],
                net_profit=totals["net_profit"] if include_sensitive else None,
                orders=totals["orders"],
                leads=totals["leads"],
                cpa=safe_div(totals["spend"], totals["orders"]),
                roas=safe_div(totals["revenue"], totals["spend"]),
            )
            for metric_date, metrics in sorted(grouped.items())
        ]


def resolve_date_range(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    today = datetime.now(UTC).date()
    end = end_date or today
    start = start_date or (end - timedelta(days=30))
    return start, end


def aggregate(metrics: list[AdMetric]) -> dict[str, Decimal | int]:
    return {
        "spend": sum((Decimal(str(metric.spend or 0)) for metric in metrics), Decimal("0")),
        "impressions": sum(int(metric.impressions or 0) for metric in metrics),
        "reach": sum(int(metric.reach or 0) for metric in metrics),
        "clicks": sum(int(metric.clicks or 0) for metric in metrics),
        "messages": sum(int(metric.messages or 0) for metric in metrics),
        "leads": sum(int(metric.leads or 0) for metric in metrics),
        "orders": sum(int(metric.orders or 0) for metric in metrics),
        "revenue": sum((Decimal(str(metric.revenue or 0)) for metric in metrics), Decimal("0")),
        "net_profit": sum((Decimal(str(metric.net_profit or 0)) for metric in metrics), Decimal("0")),
    }


def summary_from_metrics(metrics: list[AdMetric], include_sensitive: bool) -> AdvertisingSummaryResponse:
    totals = aggregate(metrics)
    return AdvertisingSummaryResponse(
        total_spend=totals["spend"],
        total_impressions=totals["impressions"],
        total_reach=totals["reach"],
        total_clicks=totals["clicks"],
        total_messages=totals["messages"],
        total_leads=totals["leads"],
        total_orders=totals["orders"],
        total_revenue=totals["revenue"],
        total_net_profit=totals["net_profit"] if include_sensitive else None,
        average_cpa=safe_div(totals["spend"], totals["orders"]),
        average_cpl=safe_div(totals["spend"], totals["leads"]),
        average_cpc=safe_div(totals["spend"], totals["clicks"]),
        average_cpm=safe_div(totals["spend"] * Decimal("1000"), totals["impressions"]),
        average_ctr=percent_div(totals["clicks"], totals["impressions"]),
        roas=safe_div(totals["revenue"], totals["spend"]),
        roi=percent_div(totals["net_profit"], totals["spend"]) if include_sensitive else None,
    )


def metric_response(metric: AdMetric, include_sensitive: bool) -> AdMetricResponse:
    return AdMetricResponse(
        id=metric.id,
        workspace_id=metric.workspace_id,
        campaign_id=metric.campaign_id,
        metric_date=metric.metric_date,
        spend=Decimal(str(metric.spend or 0)),
        impressions=int(metric.impressions or 0),
        reach=int(metric.reach or 0),
        clicks=int(metric.clicks or 0),
        messages=int(metric.messages or 0),
        leads=int(metric.leads or 0),
        orders=int(metric.orders or 0),
        revenue=Decimal(str(metric.revenue or 0)),
        net_profit=Decimal(str(metric.net_profit or 0)) if include_sensitive else None,
        cpa=safe_div(metric.spend, metric.orders),
        cpl=safe_div(metric.spend, metric.leads),
        cpc=safe_div(metric.spend, metric.clicks),
        cpm=safe_div(Decimal(str(metric.spend or 0)) * Decimal("1000"), metric.impressions),
        ctr=percent_div(metric.clicks, metric.impressions),
        roas=safe_div(metric.revenue, metric.spend),
        roi=percent_div(metric.net_profit, metric.spend) if include_sensitive else None,
    )


def safe_div(numerator, denominator) -> Decimal | None:
    denominator_decimal = Decimal(str(denominator or 0))
    if denominator_decimal == 0:
        return None
    return quantize(Decimal(str(numerator or 0)) / denominator_decimal)


def percent_div(numerator, denominator) -> Decimal | None:
    denominator_decimal = Decimal(str(denominator or 0))
    if denominator_decimal == 0:
        return None
    return quantize((Decimal(str(numerator or 0)) / denominator_decimal) * Decimal("100"))


def quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
