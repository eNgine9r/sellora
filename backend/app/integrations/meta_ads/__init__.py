"""Safe Meta Ads integration boundaries for fake-client sync simulation.

Sprint 4.7 intentionally keeps Meta Ads inactive: no live OAuth, no live API
calls, no token storage, no database writes, and no production sync jobs.
"""

from app.integrations.meta_ads.client import MetaAdsClientProtocol
from app.integrations.meta_ads.fake_client import FakeMetaAdsClient
from app.integrations.meta_ads.preview_service import MetaAdsSyncPreviewService
from app.integrations.meta_ads.sync_service import MetaAdsDryRunSyncService

__all__ = ["FakeMetaAdsClient", "MetaAdsClientProtocol", "MetaAdsDryRunSyncService", "MetaAdsSyncPreviewService"]
