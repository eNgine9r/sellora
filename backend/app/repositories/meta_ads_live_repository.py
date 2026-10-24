from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, select

from app.models.ad_campaign import AdCampaign
from app.models.ad_metric import AdMetric
from app.models.audit_log import AuditLog
from app.models.meta_ads_oauth_state import MetaAdsOAuthState
from app.models.workspace import Workspace
from app.repositories.meta_ads_connection_repository import MetaAdsConnectionRepository


class MetaAdsLiveRepository(MetaAdsConnectionRepository):
    def lock_workspace(self, workspace_id):
        # Serialize live Ads operations without blocking workspace FK KEY SHARE
        # checks (e.g. a CRM metric edit's audit while sync waits on that metric).
        # We never change the workspace key. SQLAlchemy key_share=True, read=False
        # emits PostgreSQL FOR NO KEY UPDATE, which still conflicts with itself.
        # populate_existing prevents stale identity-map state after network I/O.
        workspace = self.db.scalar(select(Workspace).where(Workspace.id == workspace_id)
            .with_for_update(key_share=True).execution_options(populate_existing=True))
        if workspace is None:
            raise ValueError("Workspace unavailable")
        self.db.expire_all()
        return workspace

    def issue_state(self, workspace_id, user_id, generation):
        state = secrets.token_urlsafe(32)
        expires = datetime.now(UTC) + timedelta(minutes=10)
        self.db.execute(delete(MetaAdsOAuthState).where(MetaAdsOAuthState.workspace_id == workspace_id))
        self.db.add(MetaAdsOAuthState(state_hash=hashlib.sha256(state.encode()).hexdigest(),
            workspace_id=workspace_id, user_id=user_id, generation=generation, expires_at=expires))
        return state, expires

    def consume_state(self, workspace_id, user_id, state):
        if not isinstance(state, str) or len(state) != 43:
            return None
        return self.db.scalar(delete(MetaAdsOAuthState).where(
            MetaAdsOAuthState.state_hash == hashlib.sha256(state.encode()).hexdigest(),
            MetaAdsOAuthState.workspace_id == workspace_id,
            MetaAdsOAuthState.user_id == user_id,
            MetaAdsOAuthState.expires_at > datetime.now(UTC),
        ).returning(MetaAdsOAuthState.generation))

    def invalidate_states(self, workspace_id):
        self.db.execute(delete(MetaAdsOAuthState).where(MetaAdsOAuthState.workspace_id == workspace_id))

    def audit(self, workspace_id, user_id, action, connection, details=None):
        self.db.add(AuditLog(workspace_id=workspace_id, user_id=user_id,
            entity_type="meta_ads_connection", entity_id=str(connection.id), action=action,
            new_value=details or {}))

    def campaigns(self, workspace_id):
        # Include archived/deleted identity rows: never silently recreate spent data.
        return self.db.scalars(select(AdCampaign).where(AdCampaign.workspace_id == workspace_id)
            .with_for_update().execution_options(populate_existing=True)).all()

    def metrics(self, workspace_id, date_from, date_to):
        return self.db.scalars(select(AdMetric).where(AdMetric.workspace_id == workspace_id,
            AdMetric.metric_date >= date_from, AdMetric.metric_date <= date_to)
            .with_for_update().execution_options(populate_existing=True)).all()

    def add_campaign(self, workspace_id, account, candidate):
        campaign = AdCampaign(workspace_id=workspace_id, name=candidate.name, platform="META",
            status="PAUSED", objective="OTHER", external_source="meta_ads",
            external_account_id=account, external_campaign_id=candidate.external_campaign_id,
            sync_source="meta_live")
        self.db.add(campaign)
        self.db.flush()
        return campaign

    def add_metric(self, workspace_id, campaign, row):
        metric = AdMetric(workspace_id=workspace_id, campaign_id=campaign.id,
            metric_date=row.date, source_type="meta_live", external_source="meta_ads",
            external_account_id=campaign.external_account_id, external_campaign_id=campaign.external_campaign_id)
        self.db.add(metric)
        return metric
