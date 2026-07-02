from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from app.integrations.meta_ads.schemas import MetaAdAccountDTO, MetaCampaignDTO, MetaInsightsRowDTO


class FakeMetaAdsClient:
    """Deterministic synthetic Meta Ads client for tests and dry-run simulation.

    This class does not accept or use access tokens and never performs HTTP
    calls. External IDs are deliberately fake and non-Meta-looking.
    """

    account_id = "fake_act_001"

    def list_ad_accounts(self) -> list[MetaAdAccountDTO]:
        return [
            MetaAdAccountDTO(
                external_account_id=self.account_id,
                name="DEMO Meta Account — Sellora QA",
                currency="UAH",
                timezone="Europe/Kyiv",
            )
        ]

    def list_campaigns(self, account_id: str) -> list[MetaCampaignDTO]:
        if account_id != self.account_id:
            return []
        created = datetime(2026, 7, 1, 9, 0, 0)
        return [
            MetaCampaignDTO(
                external_campaign_id="fake_campaign_001",
                external_account_id=account_id,
                name="DEMO Meta Campaign — Watches",
                status="ACTIVE",
                objective="MESSAGES",
                platform="META",
                created_time=created,
            ),
            MetaCampaignDTO(
                external_campaign_id="fake_campaign_002",
                external_account_id=account_id,
                name="DEMO Meta Campaign — Retargeting",
                status="PAUSED",
                objective="SALES",
                platform="META",
                created_time=created + timedelta(hours=1),
            ),
            MetaCampaignDTO(
                external_campaign_id="fake_campaign_003",
                external_account_id=account_id,
                name="DEMO Meta Campaign — No Data",
                status="ACTIVE",
                objective="AWARENESS",
                platform="META",
                created_time=created + timedelta(hours=2),
            ),
        ]

    def get_campaign_insights(self, account_id: str, date_from: date, date_to: date) -> list[MetaInsightsRowDTO]:
        if account_id != self.account_id or date_from > date_to:
            return []
        rows: list[MetaInsightsRowDTO] = []
        current = date_from
        while current <= date_to:
            rows.append(
                MetaInsightsRowDTO(
                    external_campaign_id="fake_campaign_001",
                    date=current,
                    spend=Decimal("120.50"),
                    impressions=2400,
                    clicks=180,
                    messages=24,
                    leads=8,
                    currency="UAH",
                )
            )
            rows.append(
                MetaInsightsRowDTO(
                    external_campaign_id="fake_campaign_002",
                    date=current,
                    spend=Decimal("0"),
                    impressions=0,
                    clicks=0,
                    messages=0,
                    leads=None,
                    currency="UAH",
                )
            )
            current += timedelta(days=1)
        return rows
