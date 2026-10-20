from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.integrations.meta_ads.live_reader import MetaAdsLiveReader, account_id
from app.integrations.meta_ads.live_read_only_client import MetaReadOnlyClientError
from app.integrations.meta_ads.token_crypto import decrypt_token, MetaTokenCryptoError
from app.services.meta_ads_connection_service import MetaAdsConnectionService, MetaAdsConnectionServiceError, error


class MetaAdsLiveSyncService(MetaAdsConnectionService):
    def __init__(self, db, *, reader_factory=None, **kwargs):
        super().__init__(db, **kwargs)
        self.reader_factory = reader_factory or MetaAdsLiveReader

    def _snapshot(self, workspace_id, *, selected=False):
        self._ensure_ready()
        self.repository.lock_workspace(workspace_id)
        c = self.repository.get_current(workspace_id)
        if not c or c.connection_status != "CONNECTED" or not c.encrypted_access_token or not c.generation:
            self.db.rollback()
            raise error("connection_not_ready", "Connect Meta Ads before continuing.")
        if selected and not c.external_ad_account_id:
            self.db.rollback()
            raise error("account_selection_required", "Select an advertising account first.")
        if c.token_expires_at:
            expires = c.token_expires_at.replace(tzinfo=UTC) if c.token_expires_at.tzinfo is None else c.token_expires_at
            if expires <= datetime.now(UTC):
                c.connection_status = "TOKEN_EXPIRED"
                c.last_error_code = "TOKEN_EXPIRED"
                c.last_error_message = "Meta Ads access has expired. Reconnect the account."
                self.db.commit()
                raise error("TOKEN_EXPIRED", "Meta Ads access has expired. Reconnect the account.")
        snapshot = (c.id, c.generation, c.external_ad_account_id)
        try:
            token = decrypt_token(c.encrypted_access_token, self.settings.meta_token_encryption_key)
        except MetaTokenCryptoError:
            self.db.rollback()
            raise error("credential_unavailable", "Meta Ads credential is unavailable. Reconnect.") from None
        self.db.commit()
        return snapshot, self.reader_factory(access_token=token, api_version=self.settings.meta_ads_api_version)

    def _revalidate(self, workspace_id, snapshot):
        workspace = self.repository.lock_workspace(workspace_id)
        c = self.repository.get_current(workspace_id)
        if not c or (c.id, c.generation, c.external_ad_account_id) != snapshot or c.connection_status != "CONNECTED":
            self.db.rollback()
            raise error("connection_changed", "Meta Ads connection changed during the request. Try again.")
        return workspace, c

    def _failure(self, workspace_id, user_id, snapshot, code, message):
        self.db.rollback()
        try:
            _, c = self._revalidate(workspace_id, snapshot)
        except MetaAdsConnectionServiceError:
            return
        c.last_error_code = code
        c.last_error_message = message
        if code in {"TOKEN_EXPIRED", "TOKEN_INVALID", "PERMISSION_MISSING"}:
            c.connection_status = {"TOKEN_INVALID": "NEEDS_REAUTH"}.get(code, code)
        self.repository.audit(workspace_id, user_id, "meta_ads_request_failed", c, {"code": code})
        self.db.commit()

    def accounts(self, workspace_id, user_id):
        snapshot, reader = self._snapshot(workspace_id)
        try:
            accounts = reader.list_ad_accounts()
        except MetaReadOnlyClientError as exc:
            self._failure(workspace_id, user_id, snapshot, exc.code.value, str(exc))
            raise error(exc.code.value, str(exc)) from None
        workspace, _ = self._revalidate(workspace_id, snapshot)
        response = {"accounts": [{**asdict(a), "selectable": a.currency == workspace.currency_code,
                      "reason": None if a.currency == workspace.currency_code else "currency_mismatch"} for a in accounts],
                    "selected_account_id": snapshot[2], "workspace_currency": workspace.currency_code,
                    "workspace_timezone": workspace.timezone}
        self.db.commit()
        return response

    def select_account(self, workspace_id, user_id, identifier):
        account_id(identifier)
        snapshot, reader = self._snapshot(workspace_id)
        try:
            granted = reader.list_ad_accounts()
        except MetaReadOnlyClientError as exc:
            self._failure(workspace_id, user_id, snapshot, exc.code.value, str(exc))
            raise error(exc.code.value, str(exc)) from None
        selected = next((a for a in granted if a.external_account_id == identifier), None)
        if selected is None:
            raise error("account_not_granted", "This advertising account is not available for this connection.", 403)
        workspace, c = self._revalidate(workspace_id, snapshot)
        if selected.currency != workspace.currency_code:
            self.db.rollback()
            raise error("currency_mismatch", "Advertising account and workspace currencies must match.")
        c.external_ad_account_id = selected.external_account_id
        c.account_name, c.currency, c.timezone = selected.name, selected.currency, selected.timezone
        c.generation = str(uuid4())
        c.last_error_code = c.last_error_message = None
        self.repository.audit(workspace_id, user_id, "meta_ads_account_selected", c)
        self.db.commit()
        return self.get_status(workspace_id)

    def sync(self, workspace_id, user_id, date_from, date_to):
        if not self.settings.meta_sync_enabled:
            raise error("sync_disabled", "Meta Ads manual sync is disabled.")
        if not 0 <= (date_to - date_from).days <= 90:
            raise error("invalid_date_range", "Select a range of at most 91 days.", 422)
        snapshot, reader = self._snapshot(workspace_id, selected=True)
        _, c = self._revalidate(workspace_id, snapshot)
        c.last_sync_attempt_at = datetime.now(UTC)
        self.db.commit()
        identifier = snapshot[2]
        try:
            accounts = reader.list_ad_accounts()
            selected = next((a for a in accounts if a.external_account_id == identifier), None)
            if selected is None:
                raise error("PERMISSION_MISSING", "Selected Meta Ads account access was removed. Reconnect.")
            campaigns = reader.list_campaigns(identifier)
            rows = reader.get_campaign_insights_preview(identifier, date_from, date_to)
            workspace, c = self._revalidate(workspace_id, snapshot)
            if selected.currency != workspace.currency_code or any(r.currency != selected.currency for r in rows):
                raise error("currency_mismatch", "Advertising account and workspace currencies must match.")
            result = self._import(workspace_id, identifier, campaigns, rows, date_from, date_to)
            c.currency, c.timezone = selected.currency, selected.timezone
            c.last_synced_at = datetime.now(UTC)
            c.last_error_code = c.last_error_message = None
            self.repository.audit(workspace_id, user_id, "meta_ads_sync_succeeded", c, result)
            self.db.commit()
            return {**result, "status": "SUCCEEDED", "date_from": date_from, "date_to": date_to,
                    "currency": selected.currency, "timezone": selected.timezone,
                    "workspace_timezone": workspace.timezone, "last_synced_at": c.last_synced_at,
                    "reach_measure": "not_imported"}
        except MetaReadOnlyClientError as exc:
            self._failure(workspace_id, user_id, snapshot, exc.code.value, str(exc))
            raise error(exc.code.value, str(exc)) from None
        except MetaAdsConnectionServiceError as exc:
            self._failure(workspace_id, user_id, snapshot, exc.code, exc.message)
            raise
        except IntegrityError:
            self._failure(workspace_id, user_id, snapshot, "import_conflict", "Advertising data changed. Resolve conflicts before syncing.")
            raise error("import_conflict", "Advertising data changed. Resolve conflicts before syncing.") from None

    def _import(self, workspace_id, identifier, campaigns, rows, date_from, date_to):
        existing = self.repository.campaigns(workspace_id)
        metrics = self.repository.metrics(workspace_id, date_from, date_to)
        by_id = {}
        for campaign in existing:
            if campaign.external_source == "meta_ads" and campaign.external_account_id == identifier:
                if campaign.external_campaign_id in by_id:
                    raise error("import_conflict", "Duplicate external campaign identities require review.")
                by_id[campaign.external_campaign_id] = campaign
        metric_map = {(m.campaign_id, m.metric_date): m for m in metrics}
        normalized = lambda name: " ".join(name.strip().casefold().split())
        fetched = {x.external_campaign_id for x in campaigns}
        if len(fetched) != len(campaigns) or any(x.external_account_id != identifier for x in campaigns) or any(r.external_campaign_id not in fetched for r in rows):
            raise error("invalid_provider_data", "Meta Ads returned inconsistent campaign data.")
        created_campaigns = created_metrics = updated_metrics = 0
        now = datetime.now(UTC)
        for candidate in campaigns:
            target = by_id.get(candidate.external_campaign_id)
            if target and (target.deleted_at or target.sync_source != "meta_live"):
                raise error("manual_spend_conflict", "Existing manual, CSV or archived campaign data requires review.")
            # Check name overlap even when an external identity already exists.
            if any(x is not target and x.platform in {"META", "INSTAGRAM", "FACEBOOK"}
                   and normalized(x.name) == normalized(candidate.name)
                   and x.sync_source != "meta_live" for x in existing):
                raise error("manual_spend_conflict", "A manual or CSV campaign overlaps this Meta campaign. Resolve it before syncing.")
            if target is None:
                target = self.repository.add_campaign(workspace_id, identifier, candidate)
                by_id[candidate.external_campaign_id] = target
                created_campaigns += 1
            target.name = candidate.name
            target.external_status, target.external_objective = candidate.status, candidate.objective
            target.last_synced_at = now
        seen = set()
        for row in rows:
            target = by_id[row.external_campaign_id]
            key = (target.id, row.date)
            if key in seen or not date_from <= row.date <= date_to:
                raise error("invalid_provider_data", "Meta Ads returned duplicate or invalid daily rows.")
            seen.add(key)
            metric = metric_map.get(key)
            if metric:
                if metric.deleted_at or metric.source_type != "meta_live" or metric.external_source != "meta_ads" or metric.external_account_id != identifier or metric.external_campaign_id != row.external_campaign_id:
                    raise error("manual_spend_conflict", "Manual or CSV daily metrics are protected. Resolve conflicts before syncing.")
                updated_metrics += 1
            else:
                metric = self.repository.add_metric(workspace_id, target, row)
                created_metrics += 1
            metric.spend = row.normalized_spend
            metric.impressions, metric.clicks, metric.messages = row.normalized_impressions, row.normalized_clicks, row.normalized_messages
            # CRM leads/orders/revenue/net_profit and reach are deliberately untouched.
            metric.last_synced_at = now
            metric.sync_run_id = uuid4()
        return {"campaigns_seen": len(campaigns), "metrics_seen": len(rows),
                "campaigns_created": created_campaigns, "metrics_created": created_metrics,
                "metrics_updated": updated_metrics}
