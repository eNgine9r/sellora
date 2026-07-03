from __future__ import annotations

from datetime import date
from typing import Protocol

from app.integrations.meta_ads.fake_client import FakeMetaAdsClient
from app.integrations.meta_ads.schemas import MetaAdAccountDTO, MetaCampaignDTO, MetaInsightsRowDTO


class MetaAdsReadOnlyClientProtocol(Protocol):
    """Read-only client boundary for Meta Ads discovery and preview.

    Implementations must not expose raw tokens, mutate campaigns, create metrics,
    upload customer/order data, or schedule sync work.
    """

    def list_ad_accounts(self) -> list[MetaAdAccountDTO]:
        """Return account candidates for an authorized server-side connection."""

    def list_campaigns(self, account_id: str) -> list[MetaCampaignDTO]:
        """Return campaign candidates for the selected account without DB writes."""

    def get_campaign_insights_preview(self, account_id: str, date_from: date, date_to: date) -> list[MetaInsightsRowDTO]:
        """Return preview-only delivery metrics without persisting ad metrics."""


class FakeMetaAdsReadOnlyClient:
    """Deterministic no-network read-only client for tests and previews."""

    def __init__(self) -> None:
        self._client = FakeMetaAdsClient()

    def list_ad_accounts(self) -> list[MetaAdAccountDTO]:
        return self._client.list_ad_accounts()

    def list_campaigns(self, account_id: str) -> list[MetaCampaignDTO]:
        return self._client.list_campaigns(account_id)

    def get_campaign_insights_preview(self, account_id: str, date_from: date, date_to: date) -> list[MetaInsightsRowDTO]:
        return self._client.get_campaign_insights(account_id, date_from, date_to)
