from __future__ import annotations

from datetime import date
from typing import Protocol

from app.integrations.meta_ads.schemas import MetaAdAccountDTO, MetaCampaignDTO, MetaInsightsRowDTO


class MetaAdsClientProtocol(Protocol):
    """Client boundary for future Meta Ads providers.

    Implementations must not expose raw tokens through this protocol. Sprint 4.7
    ships only a fake implementation and no live HTTP client.
    """

    def list_ad_accounts(self) -> list[MetaAdAccountDTO]:
        """Return available ad accounts for an already-authorized connection."""

    def list_campaigns(self, account_id: str) -> list[MetaCampaignDTO]:
        """Return campaigns for the selected account."""

    def get_campaign_insights(self, account_id: str, date_from: date, date_to: date) -> list[MetaInsightsRowDTO]:
        """Return daily campaign delivery metrics for the selected period."""
