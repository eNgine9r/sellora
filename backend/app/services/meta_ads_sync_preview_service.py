from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.integrations.meta_ads.read_only_client import FakeMetaAdsReadOnlyClient, MetaAdsReadOnlyClientProtocol
from app.integrations.meta_ads.token_safety import mask_token
from app.models.meta_ad_connection import MetaAdConnection, MetaAdConnectionStatus
from app.repositories.meta_ads_connection_repository import MetaAdsConnectionRepository
from app.schemas.meta_ads_read_only import (
    MetaAdAccountDiscoveryResponse,
    MetaAdAccountPreviewDTO,
    MetaCampaignDiscoveryPreviewDTO,
    MetaCampaignDiscoveryResponse,
    MetaInsightsPreviewDTO,
    MetaInsightsPreviewResponse,
    MetaReadOnlyNotReadyResponse,
)

PREVIEW_WARNING = "Preview only. Manual/CSV remains the active Advertising source."
NO_DB_WRITE_WARNING = "No ad_campaigns or ad_metrics rows are written by this preview."


@dataclass(frozen=True)
class MetaAdsReadinessResult:
    ready: bool
    reason: str | None
    message: str
    connection: MetaAdConnection | None = None


class MetaAdsSyncPreviewService:
    """Read-only account/campaign/insights discovery and sync-preview foundation."""

    def __init__(
        self,
        db: Session,
        *,
        settings: Settings | None = None,
        connection_repository: MetaAdsConnectionRepository | None = None,
        client: MetaAdsReadOnlyClientProtocol | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.connection_repository = connection_repository or MetaAdsConnectionRepository(db)
        self.client = client or FakeMetaAdsReadOnlyClient()

    def discover_accounts(self, workspace_id: UUID) -> MetaAdAccountDiscoveryResponse:
        readiness = self._readiness(workspace_id)
        if not readiness.ready:
            return MetaAdAccountDiscoveryResponse(**self._not_ready_payload(readiness))
        accounts = [
            MetaAdAccountPreviewDTO(
                external_account_id_masked=mask_token(account.external_account_id),
                name=account.name,
                currency=account.currency,
                timezone=account.timezone,
                can_be_selected=True,
                warnings=[PREVIEW_WARNING, NO_DB_WRITE_WARNING],
            )
            for account in self.client.list_ad_accounts()
        ]
        return MetaAdAccountDiscoveryResponse(ready=True, reason=None, message="Meta Ads account discovery preview is available.", accounts=accounts)

    def discover_campaigns(self, workspace_id: UUID, account_id: str | None = None) -> MetaCampaignDiscoveryResponse:
        readiness = self._readiness(workspace_id)
        if not readiness.ready:
            return MetaCampaignDiscoveryResponse(**self._not_ready_payload(readiness))
        selected_account_id = account_id or self._default_account_id()
        campaigns = [
            MetaCampaignDiscoveryPreviewDTO(
                external_campaign_id_masked=mask_token(campaign.external_campaign_id),
                name=campaign.name,
                status=campaign.status,
                objective=campaign.objective,
                start_time=campaign.created_time,
                warnings=[PREVIEW_WARNING, NO_DB_WRITE_WARNING],
            )
            for campaign in self.client.list_campaigns(selected_account_id)
        ]
        return MetaCampaignDiscoveryResponse(ready=True, reason=None, message="Meta Ads campaign discovery preview is available.", campaigns=campaigns)

    def preview_insights(self, workspace_id: UUID, date_from: date, date_to: date, account_id: str | None = None) -> MetaInsightsPreviewResponse:
        readiness = self._readiness(workspace_id)
        if not readiness.ready:
            return MetaInsightsPreviewResponse(**self._not_ready_payload(readiness))
        if date_from > date_to:
            return MetaInsightsPreviewResponse(ready=False, reason="invalid_date_range", message="Meta Ads preview date range is invalid.")
        selected_account_id = account_id or self._default_account_id()
        campaigns_by_id = {campaign.external_campaign_id: campaign for campaign in self.client.list_campaigns(selected_account_id)}
        insights = []
        for row in self.client.get_campaign_insights_preview(selected_account_id, date_from, date_to):
            campaign = campaigns_by_id.get(row.external_campaign_id)
            insights.append(
                MetaInsightsPreviewDTO(
                    date=row.date,
                    campaign_name=campaign.name if campaign else "Unknown Meta campaign",
                    external_campaign_id_masked=mask_token(row.external_campaign_id),
                    spend=row.normalized_spend,
                    impressions=row.normalized_impressions,
                    clicks=row.normalized_clicks,
                    reach=None,
                    messages=row.normalized_messages,
                    warnings=[PREVIEW_WARNING, NO_DB_WRITE_WARNING],
                )
            )
        return MetaInsightsPreviewResponse(ready=True, reason=None, message="Meta Ads insights sync preview is available.", insights=insights)

    def _readiness(self, workspace_id: UUID) -> MetaAdsReadinessResult:
        if not self.settings.meta_sync_preview_enabled:
            return MetaAdsReadinessResult(False, "feature_disabled", "Meta Ads discovery is not available yet.")
        if not self.settings.meta_connections_enabled:
            return MetaAdsReadinessResult(False, "feature_disabled", "Meta Ads connection foundation is disabled.")
        connection = self.connection_repository.get_current(workspace_id)
        if connection is None:
            return MetaAdsReadinessResult(False, "connection_not_ready", "Meta Ads discovery is not available yet.")
        status = MetaAdConnectionStatus(connection.connection_status)
        if status not in {MetaAdConnectionStatus.CONNECTED, MetaAdConnectionStatus.MOCK_ONLY}:
            return MetaAdsReadinessResult(False, "connection_not_ready", "Meta Ads connection is not ready for discovery preview.", connection)
        if status == MetaAdConnectionStatus.CONNECTED and not connection.encrypted_access_token:
            return MetaAdsReadinessResult(False, "token_missing", "Meta Ads connection token is not available for read-only preview.", connection)
        if self.settings.meta_sync_enabled:
            return MetaAdsReadinessResult(False, "sync_must_remain_disabled", "Meta Ads production sync must remain disabled for preview.", connection)
        return MetaAdsReadinessResult(True, None, "Meta Ads read-only preview is ready.", connection)

    def _not_ready_payload(self, readiness: MetaAdsReadinessResult) -> dict[str, object]:
        return MetaReadOnlyNotReadyResponse(reason=readiness.reason or "not_ready", message=readiness.message).model_dump()

    def _default_account_id(self) -> str:
        accounts = self.client.list_ad_accounts()
        return accounts[0].external_account_id if accounts else ""
