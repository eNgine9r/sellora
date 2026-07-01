from datetime import date
from uuid import uuid4

from app.integrations.meta_ads.fake_client import FakeMetaAdsClient
from app.integrations.meta_ads.mapper import META_SYNC_SOURCE, map_campaign_to_candidate, map_insights_to_metric_candidate
from app.integrations.meta_ads.sync_service import MetaAdsDryRunSyncService


def test_mapper_creates_campaign_and_metric_candidates_without_db_write() -> None:
    workspace_id = uuid4()
    client = FakeMetaAdsClient()
    campaign = client.list_campaigns("fake_act_001")[0]
    insight = client.get_campaign_insights("fake_act_001", date(2026, 7, 1), date(2026, 7, 1))[0]

    campaign_candidate = map_campaign_to_candidate(campaign, workspace_id=workspace_id)
    metric_candidate = map_insights_to_metric_candidate(insight, workspace_id=workspace_id)

    assert campaign_candidate.workspace_id == workspace_id
    assert campaign_candidate.external_source == META_SYNC_SOURCE
    assert campaign_candidate.external_campaign_id == "fake_campaign_001"
    assert metric_candidate.workspace_id == workspace_id
    assert metric_candidate.external_source == META_SYNC_SOURCE
    assert metric_candidate.spend == insight.normalized_spend
    assert "orders" not in metric_candidate.__dict__
    assert "revenue" not in metric_candidate.__dict__
    assert "net_profit" not in metric_candidate.__dict__


def test_mapper_does_not_add_workspace_id_unless_service_supplies_it() -> None:
    client = FakeMetaAdsClient()
    campaign = client.list_campaigns("fake_act_001")[0]

    candidate = map_campaign_to_candidate(campaign)

    assert candidate.workspace_id is None


def test_dry_run_sync_returns_counts_candidates_and_user_safe_issues() -> None:
    workspace_id = uuid4()
    service = MetaAdsDryRunSyncService(client=FakeMetaAdsClient())

    result = service.simulate_sync(workspace_id, "fake_act_001", date(2026, 7, 1), date(2026, 7, 2))

    assert result.dry_run is True
    assert result.campaigns_seen == 3
    assert result.metrics_seen == 4
    assert result.campaigns_to_create == 3
    assert result.campaigns_to_update == 0
    assert result.metrics_to_create == 4
    assert result.metrics_to_update == 0
    assert result.skipped == 1
    assert result.issues[0].code == "campaign_has_no_metrics"
    assert result.issues[0].external_campaign_id == "fake_campaign_003"
    assert all(candidate.workspace_id == workspace_id for candidate in result.campaign_candidates)
    assert all(candidate.workspace_id == workspace_id for candidate in result.metric_candidates)
    assert "token" not in result.issues[0].message.lower()


def test_dry_run_invalid_date_range_is_safe_and_has_no_candidates() -> None:
    service = MetaAdsDryRunSyncService(client=FakeMetaAdsClient())

    result = service.simulate_sync(uuid4(), "fake_act_001", date(2026, 7, 2), date(2026, 7, 1))

    assert result.dry_run is True
    assert result.campaigns_seen == 0
    assert result.metrics_seen == 0
    assert result.campaign_candidates == []
    assert result.metric_candidates == []
    assert result.issues[0].code == "invalid_date_range"
