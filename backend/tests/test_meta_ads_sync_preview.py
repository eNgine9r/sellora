from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.integrations.meta_ads.fake_client import FakeMetaAdsClient
from app.integrations.meta_ads.preview_service import MetaAdsSyncPreviewService
from app.integrations.meta_ads.repository import ExistingAdCampaignSnapshot, ExistingAdMetricSnapshot
from app.integrations.meta_ads.schemas import POTENTIAL_CONFLICT, WOULD_CREATE, WOULD_SKIP, WOULD_UPDATE


@dataclass
class InMemoryAdvertisingSyncReadRepository:
    campaigns: list[ExistingAdCampaignSnapshot] = field(default_factory=list)
    metrics: list[ExistingAdMetricSnapshot] = field(default_factory=list)
    writes_attempted: int = 0

    def list_campaign_snapshots(self, workspace_id: UUID) -> list[ExistingAdCampaignSnapshot]:
        return [campaign for campaign in self.campaigns if campaign.workspace_id == workspace_id]

    def list_metric_snapshots(self, workspace_id: UUID, date_from: date, date_to: date) -> list[ExistingAdMetricSnapshot]:
        return [metric for metric in self.metrics if metric.workspace_id == workspace_id and date_from <= metric.metric_date <= date_to]


def campaign_snapshot(workspace_id: UUID, name: str = "DEMO Meta Campaign — Watches", platform: str = "META", status: str = "ACTIVE") -> ExistingAdCampaignSnapshot:
    return ExistingAdCampaignSnapshot(id=uuid4(), workspace_id=workspace_id, name=name, platform=platform, status=status, created_at=datetime(2026, 7, 1, 9, 0, 0))


def metric_snapshot(workspace_id: UUID, campaign_id: UUID, metric_date: date = date(2026, 7, 1)) -> ExistingAdMetricSnapshot:
    return ExistingAdMetricSnapshot(
        id=uuid4(),
        workspace_id=workspace_id,
        campaign_id=campaign_id,
        campaign_name="DEMO Meta Campaign — Watches",
        metric_date=metric_date,
        spend=Decimal("50.00"),
        impressions=100,
        clicks=10,
        messages=2,
        leads=1,
        orders=1,
        revenue=Decimal("200.00"),
        net_profit=Decimal("70.00"),
        source_label="manual_or_csv",
    )


def preview(repository: InMemoryAdvertisingSyncReadRepository, workspace_id: UUID | None = None):
    service = MetaAdsSyncPreviewService(client=FakeMetaAdsClient())
    return service.preview_sync(workspace_id or uuid4(), "fake_act_001", date(2026, 7, 1), date(2026, 7, 1), repository)


def test_preview_empty_repository_returns_create_items_and_external_id_note() -> None:
    result = preview(InMemoryAdvertisingSyncReadRepository())

    assert result.dry_run is True
    assert result.db_writes is False
    assert result.summary.campaigns_would_create == 3
    assert result.summary.metrics_would_create == 2
    assert result.summary.needs_external_id_support == 5
    assert result.issues[0].code == "campaign_has_no_metrics"
    assert {item.classification for item in result.campaign_items} == {WOULD_CREATE}
    assert {item.classification for item in result.metric_items} == {WOULD_CREATE}


def test_existing_campaign_name_platform_match_can_skip_or_update() -> None:
    workspace_id = uuid4()
    existing_skip = campaign_snapshot(workspace_id, status="ACTIVE")
    existing_update = campaign_snapshot(workspace_id, name="DEMO Meta Campaign — Retargeting", status="ACTIVE")
    repository = InMemoryAdvertisingSyncReadRepository(campaigns=[existing_skip, existing_update])

    result = preview(repository, workspace_id)

    by_external_id = {item.external_campaign_id: item for item in result.campaign_items}
    assert by_external_id["fake_campaign_001"].classification == WOULD_SKIP
    assert by_external_id["fake_campaign_001"].matched_campaign_id == existing_skip.id
    assert by_external_id["fake_campaign_002"].classification == WOULD_UPDATE
    assert by_external_id["fake_campaign_002"].matched_campaign_id == existing_update.id


def test_ambiguous_campaign_matches_return_potential_conflict() -> None:
    workspace_id = uuid4()
    repository = InMemoryAdvertisingSyncReadRepository(campaigns=[campaign_snapshot(workspace_id), campaign_snapshot(workspace_id)])

    result = preview(repository, workspace_id)

    campaign_item = next(item for item in result.campaign_items if item.external_campaign_id == "fake_campaign_001")
    metric_item = next(item for item in result.metric_items if item.external_campaign_id == "fake_campaign_001")
    assert campaign_item.classification == POTENTIAL_CONFLICT
    assert len(campaign_item.conflicts) == 2
    assert metric_item.classification == POTENTIAL_CONFLICT
    assert result.summary.potential_conflicts >= 2


def test_existing_manual_metric_same_campaign_date_is_flagged_not_overwritten() -> None:
    workspace_id = uuid4()
    existing_campaign = campaign_snapshot(workspace_id)
    repository = InMemoryAdvertisingSyncReadRepository(campaigns=[existing_campaign], metrics=[metric_snapshot(workspace_id, existing_campaign.id)])

    result = preview(repository, workspace_id)

    metric_item = next(item for item in result.metric_items if item.external_campaign_id == "fake_campaign_001")
    assert metric_item.classification == POTENTIAL_CONFLICT
    assert metric_item.matched_metric_id == repository.metrics[0].id
    assert metric_item.conflicts[0].code == "manual_metric_overlap"
    assert result.summary.metrics_would_update == 0
    assert repository.writes_attempted == 0


def test_unrelated_workspace_data_is_ignored() -> None:
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    repository = InMemoryAdvertisingSyncReadRepository(campaigns=[campaign_snapshot(other_workspace_id)])

    result = preview(repository, workspace_id)

    campaign_item = next(item for item in result.campaign_items if item.external_campaign_id == "fake_campaign_001")
    assert campaign_item.classification == WOULD_CREATE
    assert campaign_item.matched_campaign_id is None


def test_preview_excludes_orders_revenue_and_profit_from_meta_metric_items() -> None:
    result = preview(InMemoryAdvertisingSyncReadRepository())
    metric_item = result.metric_items[0]

    assert "orders" not in metric_item.__dict__
    assert "revenue" not in metric_item.__dict__
    assert "net_profit" not in metric_item.__dict__
    assert metric_item.spend == Decimal("120.50")


def test_invalid_date_range_returns_user_safe_issue() -> None:
    service = MetaAdsSyncPreviewService(client=FakeMetaAdsClient())

    result = service.preview_sync(uuid4(), "fake_act_001", date(2026, 7, 2), date(2026, 7, 1), InMemoryAdvertisingSyncReadRepository())

    assert result.dry_run is True
    assert result.db_writes is False
    assert result.summary.invalid_rows == 1
    assert result.issues[0].code == "invalid_date_range"
    assert "token" not in result.issues[0].message.lower()
