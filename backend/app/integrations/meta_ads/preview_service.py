from __future__ import annotations

from collections import defaultdict
from datetime import date
from uuid import UUID

from app.integrations.meta_ads.client import MetaAdsClientProtocol
from app.integrations.meta_ads.fake_client import FakeMetaAdsClient
from app.integrations.meta_ads.mapper import map_campaign_to_candidate, map_insights_to_metric_candidate
from app.integrations.meta_ads.repository import AdvertisingSyncReadRepository, ExistingAdCampaignSnapshot, ExistingAdMetricSnapshot
from app.integrations.meta_ads.schemas import (
    INVALID,
    POTENTIAL_CONFLICT,
    WOULD_CREATE,
    WOULD_SKIP,
    WOULD_UPDATE,
    AdCampaignSyncCandidate,
    AdMetricSyncCandidate,
    MetaCampaignPreviewItemDTO,
    MetaMetricPreviewItemDTO,
    MetaSyncConflictDTO,
    MetaSyncIssueDTO,
    MetaSyncPreviewResultDTO,
    MetaSyncPreviewSummaryDTO,
)

EXTERNAL_ID_SUPPORT_MESSAGE = "Sellora does not yet store Meta external IDs. Review before enabling live sync."
EXTERNAL_ID_MATCH_MESSAGE = "Matched by workspace-scoped external identity."
MANUAL_METRIC_CONFLICT_MESSAGE = "Existing manual/CSV metric is protected and will not be overwritten by Meta preview."
AMBIGUOUS_CAMPAIGN_MESSAGE = "Multiple existing campaigns match by name/platform. Review before enabling live sync."


def normalize_campaign_key(name: str, platform: str) -> tuple[str, str]:
    return (" ".join(name.strip().lower().split()), platform.strip().upper())


def external_identity_key(external_source: str | None, external_account_id: str | None, external_campaign_id: str | None) -> tuple[str, str, str] | None:
    if not external_source or not external_account_id or not external_campaign_id:
        return None
    return (external_source.strip().lower(), external_account_id.strip(), external_campaign_id.strip())


class MetaAdsSyncPreviewService:
    """Read-only sync preview for future Meta Ads sync.

    The preview uses fake/client-protocol data plus a read-only repository. It
    never writes to the database, never schedules jobs, never uses tokens, and
    never calls live Meta APIs by default.
    """

    def __init__(self, client: MetaAdsClientProtocol | None = None) -> None:
        self.client = client or FakeMetaAdsClient()

    def preview_sync(self, workspace_id: UUID, account_id: str, date_from: date, date_to: date, read_repository: AdvertisingSyncReadRepository) -> MetaSyncPreviewResultDTO:
        if date_from > date_to:
            return self._invalid_date_range_result()

        campaigns = self.client.list_campaigns(account_id)
        insights = self.client.get_campaign_insights(account_id, date_from, date_to)
        campaign_candidates = [map_campaign_to_candidate(campaign, workspace_id=workspace_id) for campaign in campaigns]
        metric_candidates = [map_insights_to_metric_candidate(row, workspace_id=workspace_id) for row in insights]

        existing_campaigns = [snapshot for snapshot in read_repository.list_campaign_snapshots(workspace_id) if snapshot.workspace_id == workspace_id]
        existing_metrics = [snapshot for snapshot in read_repository.list_metric_snapshots(workspace_id, date_from, date_to) if snapshot.workspace_id == workspace_id]

        campaign_items, campaign_matches = self._preview_campaigns(campaign_candidates, existing_campaigns)
        campaign_candidates_by_id = {candidate.external_campaign_id: candidate for candidate in campaign_candidates}
        metric_items = self._preview_metrics(metric_candidates, campaign_candidates_by_id, campaign_matches, campaign_items, existing_metrics)
        issues = self._no_metric_issues(campaign_candidates, metric_candidates)
        summary = self._summary(campaign_items, metric_items, issues)
        return MetaSyncPreviewResultDTO(summary=summary, campaign_items=campaign_items, metric_items=metric_items, issues=issues)

    def _preview_campaigns(self, candidates: list[AdCampaignSyncCandidate], existing_campaigns: list[ExistingAdCampaignSnapshot]) -> tuple[list[MetaCampaignPreviewItemDTO], dict[str, ExistingAdCampaignSnapshot | None]]:
        by_external_identity: dict[tuple[str, str, str], ExistingAdCampaignSnapshot] = {}
        by_key: dict[tuple[str, str], list[ExistingAdCampaignSnapshot]] = defaultdict(list)
        for campaign in existing_campaigns:
            identity_key = external_identity_key(campaign.external_source, campaign.external_account_id, campaign.external_campaign_id)
            if identity_key is not None:
                by_external_identity[identity_key] = campaign
            by_key[normalize_campaign_key(campaign.name, campaign.platform)].append(campaign)

        items: list[MetaCampaignPreviewItemDTO] = []
        matches: dict[str, ExistingAdCampaignSnapshot | None] = {}
        for candidate in candidates:
            candidate_identity_key = external_identity_key(candidate.external_source, candidate.external_account_id, candidate.external_campaign_id)
            existing_by_identity = by_external_identity.get(candidate_identity_key) if candidate_identity_key else None
            if existing_by_identity is not None:
                matches[candidate.external_campaign_id] = existing_by_identity
                classification = WOULD_SKIP if existing_by_identity.status == candidate.status else WOULD_UPDATE
                message = EXTERNAL_ID_MATCH_MESSAGE if classification == WOULD_SKIP else f"External identity match would review campaign status: {existing_by_identity.status} → {candidate.status}."
                items.append(
                    MetaCampaignPreviewItemDTO(
                        external_campaign_id=candidate.external_campaign_id,
                        name=candidate.name,
                        platform=candidate.platform,
                        classification=classification,
                        matched_campaign_id=existing_by_identity.id,
                        needs_external_id_support=False,
                        message=message,
                    )
                )
                continue
            key = normalize_campaign_key(candidate.name, candidate.platform)
            matched = by_key.get(key, [])
            if not matched:
                matches[candidate.external_campaign_id] = None
                items.append(MetaCampaignPreviewItemDTO(external_campaign_id=candidate.external_campaign_id, name=candidate.name, platform=candidate.platform, classification=WOULD_CREATE, message=EXTERNAL_ID_SUPPORT_MESSAGE))
                continue
            if len(matched) > 1:
                matches[candidate.external_campaign_id] = None
                items.append(
                    MetaCampaignPreviewItemDTO(
                        external_campaign_id=candidate.external_campaign_id,
                        name=candidate.name,
                        platform=candidate.platform,
                        classification=POTENTIAL_CONFLICT,
                        message=AMBIGUOUS_CAMPAIGN_MESSAGE,
                        conflicts=[MetaSyncConflictDTO(code="ambiguous_campaign_match", message=AMBIGUOUS_CAMPAIGN_MESSAGE, external_campaign_id=candidate.external_campaign_id, existing_id=campaign.id) for campaign in matched],
                    )
                )
                continue
            existing = matched[0]
            matches[candidate.external_campaign_id] = existing
            classification = WOULD_SKIP if existing.status == candidate.status else WOULD_UPDATE
            message = EXTERNAL_ID_SUPPORT_MESSAGE if classification == WOULD_SKIP else f"Existing campaign status would be reviewed: {existing.status} → {candidate.status}."
            items.append(MetaCampaignPreviewItemDTO(external_campaign_id=candidate.external_campaign_id, name=candidate.name, platform=candidate.platform, classification=classification, matched_campaign_id=existing.id, message=message))
        return items, matches

    def _preview_metrics(self, candidates: list[AdMetricSyncCandidate], campaign_candidates_by_id: dict[str, AdCampaignSyncCandidate], campaign_matches: dict[str, ExistingAdCampaignSnapshot | None], campaign_items: list[MetaCampaignPreviewItemDTO], existing_metrics: list[ExistingAdMetricSnapshot]) -> list[MetaMetricPreviewItemDTO]:
        metrics_by_external_identity_date: dict[tuple[str, str, str, date], list[ExistingAdMetricSnapshot]] = defaultdict(list)
        metrics_by_campaign_date: dict[tuple[UUID, date], list[ExistingAdMetricSnapshot]] = defaultdict(list)
        for metric in existing_metrics:
            identity_key = external_identity_key(metric.external_source, metric.external_account_id, metric.external_campaign_id)
            if identity_key is not None:
                metrics_by_external_identity_date[(*identity_key, metric.metric_date)].append(metric)
            metrics_by_campaign_date[(metric.campaign_id, metric.metric_date)].append(metric)

        conflict_campaign_ids = {item.external_campaign_id for item in campaign_items if item.classification == POTENTIAL_CONFLICT}
        items: list[MetaMetricPreviewItemDTO] = []
        for candidate in candidates:
            campaign_candidate = campaign_candidates_by_id.get(candidate.external_campaign_id)
            candidate_identity_key = external_identity_key(
                candidate.external_source,
                campaign_candidate.external_account_id if campaign_candidate else None,
                candidate.external_campaign_id,
            )
            if candidate_identity_key is not None:
                existing_by_identity = metrics_by_external_identity_date.get((*candidate_identity_key, candidate.metric_date), [])
                if existing_by_identity:
                    existing_metric = existing_by_identity[0]
                    classification = WOULD_SKIP if self._metric_matches_candidate(existing_metric, candidate) else WOULD_UPDATE
                    items.append(
                        self._metric_item(
                            candidate,
                            classification,
                            matched_campaign_id=existing_metric.campaign_id,
                            matched_metric_id=existing_metric.id,
                            message=EXTERNAL_ID_MATCH_MESSAGE,
                            needs_external_id_support=False,
                        )
                    )
                    continue
            campaign_match = campaign_matches.get(candidate.external_campaign_id)
            if candidate.external_campaign_id in conflict_campaign_ids:
                items.append(self._metric_item(candidate, POTENTIAL_CONFLICT, message="Metric cannot be matched safely until campaign conflict is resolved."))
                continue
            if campaign_match is None:
                items.append(self._metric_item(candidate, WOULD_CREATE, message=EXTERNAL_ID_SUPPORT_MESSAGE))
                continue
            existing = metrics_by_campaign_date.get((campaign_match.id, candidate.metric_date), [])
            if not existing:
                items.append(self._metric_item(candidate, WOULD_CREATE, matched_campaign_id=campaign_match.id, message=EXTERNAL_ID_SUPPORT_MESSAGE))
                continue
            conflict = existing[0]
            items.append(
                self._metric_item(
                    candidate,
                    POTENTIAL_CONFLICT,
                    matched_campaign_id=campaign_match.id,
                    matched_metric_id=conflict.id,
                    message=MANUAL_METRIC_CONFLICT_MESSAGE,
                    conflicts=[MetaSyncConflictDTO(code="manual_metric_overlap", message=MANUAL_METRIC_CONFLICT_MESSAGE, external_campaign_id=candidate.external_campaign_id, existing_id=conflict.id)],
                )
            )
        return items

    def _metric_item(self, candidate: AdMetricSyncCandidate, classification: str, matched_campaign_id: UUID | None = None, matched_metric_id: UUID | None = None, message: str = "", conflicts: list[MetaSyncConflictDTO] | None = None, needs_external_id_support: bool = True) -> MetaMetricPreviewItemDTO:
        return MetaMetricPreviewItemDTO(
            external_campaign_id=candidate.external_campaign_id,
            metric_date=candidate.metric_date,
            classification=classification,
            matched_campaign_id=matched_campaign_id,
            matched_metric_id=matched_metric_id,
            spend=candidate.spend,
            impressions=candidate.impressions,
            clicks=candidate.clicks,
            messages=candidate.messages,
            leads=candidate.leads,
            currency=candidate.currency,
            needs_external_id_support=needs_external_id_support,
            message=message,
            conflicts=conflicts or [],
        )

    def _metric_matches_candidate(self, existing_metric: ExistingAdMetricSnapshot, candidate: AdMetricSyncCandidate) -> bool:
        return (
            existing_metric.spend == candidate.spend
            and existing_metric.impressions == candidate.impressions
            and existing_metric.clicks == candidate.clicks
            and existing_metric.messages == candidate.messages
            and existing_metric.leads == candidate.leads
        )

    def _no_metric_issues(self, campaign_candidates: list[AdCampaignSyncCandidate], metric_candidates: list[AdMetricSyncCandidate]) -> list[MetaSyncIssueDTO]:
        campaigns_with_metrics = {candidate.external_campaign_id for candidate in metric_candidates}
        return [MetaSyncIssueDTO(code="campaign_has_no_metrics", message="Campaign has no delivery metrics in the selected period.", external_campaign_id=campaign.external_campaign_id) for campaign in campaign_candidates if campaign.external_campaign_id not in campaigns_with_metrics]

    def _summary(self, campaign_items: list[MetaCampaignPreviewItemDTO], metric_items: list[MetaMetricPreviewItemDTO], issues: list[MetaSyncIssueDTO]) -> MetaSyncPreviewSummaryDTO:
        return MetaSyncPreviewSummaryDTO(
            campaigns_seen=len(campaign_items),
            metrics_seen=len(metric_items),
            campaigns_would_create=sum(item.classification == WOULD_CREATE for item in campaign_items),
            campaigns_would_update=sum(item.classification == WOULD_UPDATE for item in campaign_items),
            campaigns_would_skip=sum(item.classification == WOULD_SKIP for item in campaign_items),
            metrics_would_create=sum(item.classification == WOULD_CREATE for item in metric_items),
            metrics_would_update=sum(item.classification == WOULD_UPDATE for item in metric_items),
            metrics_would_skip=sum(item.classification == WOULD_SKIP for item in metric_items),
            potential_conflicts=sum(item.classification == POTENTIAL_CONFLICT for item in [*campaign_items, *metric_items]),
            needs_external_id_support=sum(item.needs_external_id_support for item in [*campaign_items, *metric_items]),
            invalid_rows=sum(issue.code == "invalid_date_range" for issue in issues),
        )

    def _invalid_date_range_result(self) -> MetaSyncPreviewResultDTO:
        issue = MetaSyncIssueDTO(code="invalid_date_range", message="Date range start must be before or equal to end date.")
        summary = MetaSyncPreviewSummaryDTO(
            campaigns_seen=0,
            metrics_seen=0,
            campaigns_would_create=0,
            campaigns_would_update=0,
            campaigns_would_skip=0,
            metrics_would_create=0,
            metrics_would_update=0,
            metrics_would_skip=0,
            potential_conflicts=0,
            needs_external_id_support=0,
            invalid_rows=1,
        )
        return MetaSyncPreviewResultDTO(summary=summary, issues=[issue])
