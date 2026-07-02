from __future__ import annotations

from datetime import date
from uuid import UUID

from app.integrations.meta_ads.client import MetaAdsClientProtocol
from app.integrations.meta_ads.fake_client import FakeMetaAdsClient
from app.integrations.meta_ads.mapper import map_campaign_to_candidate, map_insights_to_metric_candidate
from app.integrations.meta_ads.schemas import MetaSyncIssueDTO, MetaSyncResultDTO


class MetaAdsDryRunSyncService:
    """Pure dry-run sync simulation for future Meta Ads integration.

    The service does not write to the database, does not schedule jobs, does not
    call live Meta APIs, and does not handle credentials. `workspace_id` must be
    supplied by trusted backend context in future route/service wiring.
    """

    def __init__(self, client: MetaAdsClientProtocol | None = None) -> None:
        self.client = client or FakeMetaAdsClient()

    def simulate_sync(self, workspace_id: UUID, account_id: str, date_from: date, date_to: date) -> MetaSyncResultDTO:
        if date_from > date_to:
            return MetaSyncResultDTO(
                campaigns_seen=0,
                metrics_seen=0,
                campaigns_to_create=0,
                campaigns_to_update=0,
                metrics_to_create=0,
                metrics_to_update=0,
                skipped=0,
                issues=[MetaSyncIssueDTO(code="invalid_date_range", message="Date range start must be before or equal to end date.")],
            )

        campaigns = self.client.list_campaigns(account_id)
        insights = self.client.get_campaign_insights(account_id, date_from, date_to)
        campaign_candidates = [map_campaign_to_candidate(campaign, workspace_id=workspace_id) for campaign in campaigns]
        metric_candidates = [map_insights_to_metric_candidate(row, workspace_id=workspace_id) for row in insights]

        campaigns_with_metrics = {candidate.external_campaign_id for candidate in metric_candidates}
        issues = [
            MetaSyncIssueDTO(
                code="campaign_has_no_metrics",
                message="Campaign has no delivery metrics in the selected period.",
                external_campaign_id=campaign.external_campaign_id,
            )
            for campaign in campaign_candidates
            if campaign.external_campaign_id not in campaigns_with_metrics
        ]

        return MetaSyncResultDTO(
            campaigns_seen=len(campaigns),
            metrics_seen=len(insights),
            campaigns_to_create=len(campaign_candidates),
            campaigns_to_update=0,
            metrics_to_create=len(metric_candidates),
            metrics_to_update=0,
            skipped=len(issues),
            issues=issues,
            campaign_candidates=campaign_candidates,
            metric_candidates=metric_candidates,
        )
