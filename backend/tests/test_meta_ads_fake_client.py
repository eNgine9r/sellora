from datetime import date
from decimal import Decimal

from app.integrations.meta_ads.client import MetaAdsClientProtocol
from app.integrations.meta_ads.fake_client import FakeMetaAdsClient
from app.integrations.meta_ads.schemas import MetaInsightsRowDTO


def test_fake_client_follows_protocol_without_token() -> None:
    client: MetaAdsClientProtocol = FakeMetaAdsClient()

    accounts = client.list_ad_accounts()

    assert accounts[0].external_account_id == "fake_act_001"
    assert accounts[0].name == "DEMO Meta Account — Sellora QA"
    assert "token" not in accounts[0].__dict__


def test_fake_client_returns_synthetic_campaigns_only() -> None:
    client = FakeMetaAdsClient()

    campaigns = client.list_campaigns("fake_act_001")

    assert [campaign.external_campaign_id for campaign in campaigns] == ["fake_campaign_001", "fake_campaign_002", "fake_campaign_003"]
    assert {campaign.name for campaign in campaigns} == {
        "DEMO Meta Campaign — Watches",
        "DEMO Meta Campaign — Retargeting",
        "DEMO Meta Campaign — No Data",
    }
    assert all(not campaign.external_campaign_id.startswith("act_") for campaign in campaigns)


def test_fake_client_returns_deterministic_insights_with_zero_denominator_case() -> None:
    client = FakeMetaAdsClient()

    first = client.get_campaign_insights("fake_act_001", date(2026, 7, 1), date(2026, 7, 2))
    second = client.get_campaign_insights("fake_act_001", date(2026, 7, 1), date(2026, 7, 2))

    assert first == second
    assert len(first) == 4
    assert first[0].spend == Decimal("120.50")
    zero_row = next(row for row in first if row.external_campaign_id == "fake_campaign_002")
    assert zero_row.normalized_spend == Decimal("0.00")
    assert zero_row.normalized_clicks == 0
    assert zero_row.normalized_leads == 0


def test_insights_dto_normalizes_missing_values_and_excludes_business_metrics() -> None:
    row = MetaInsightsRowDTO(external_campaign_id="fake_campaign_001", date=date(2026, 7, 1), spend="10.5", impressions="3", clicks=None, messages=None, leads=None)

    assert row.normalized_spend == Decimal("10.50")
    assert row.normalized_impressions == 3
    assert row.normalized_clicks == 0
    assert "orders" not in row.__dict__
    assert "revenue" not in row.__dict__
    assert "net_profit" not in row.__dict__
