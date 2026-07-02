from __future__ import annotations

from uuid import UUID

from app.integrations.meta_ads.schemas import AdCampaignSyncCandidate, AdMetricSyncCandidate, MetaCampaignDTO, MetaInsightsRowDTO

META_SYNC_SOURCE = "META_FAKE"


def map_campaign_to_candidate(campaign: MetaCampaignDTO, workspace_id: UUID | None = None) -> AdCampaignSyncCandidate:
    return AdCampaignSyncCandidate(
        external_source=META_SYNC_SOURCE,
        external_campaign_id=campaign.external_campaign_id,
        external_account_id=campaign.external_account_id,
        name=campaign.name,
        platform=campaign.platform,
        status=campaign.status,
        objective=campaign.objective,
        workspace_id=workspace_id,
    )


def map_insights_to_metric_candidate(row: MetaInsightsRowDTO, workspace_id: UUID | None = None) -> AdMetricSyncCandidate:
    return AdMetricSyncCandidate(
        external_source=META_SYNC_SOURCE,
        external_campaign_id=row.external_campaign_id,
        metric_date=row.date,
        spend=row.normalized_spend,
        impressions=row.normalized_impressions,
        clicks=row.normalized_clicks,
        messages=row.normalized_messages,
        leads=row.normalized_leads,
        currency=row.currency,
        workspace_id=workspace_id,
    )
