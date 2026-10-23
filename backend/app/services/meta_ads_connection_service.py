from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse, urlencode
from uuid import UUID, uuid4

from cryptography.fernet import Fernet

from app.core.config import Settings, get_settings
from app.integrations.meta_ads.graph_transport import SUPPORTED_ADS_VERSIONS
from app.integrations.meta_ads.live_oauth_client import MetaLiveOAuthClient, MetaLiveOAuthClientError, build_meta_oauth_authorization_url
from app.integrations.meta_ads.token_crypto import MetaTokenCryptoError, encrypt_token
from app.models.meta_ad_connection import MetaAdConnectionStatus
from app.repositories.meta_ads_live_repository import MetaAdsLiveRepository
from app.schemas.meta_ads_connection import MetaAdsConnectionStatusResponse, MetaAdsDisconnectResponse, MetaAdsOAuthCallbackResponse, MetaAdsOAuthStartResponse


@dataclass(frozen=True)
class MetaAdsConnectionServiceError(Exception):
    status_code: int
    code: str
    message: str

    def __str__(self):
        return self.message


def error(code, message, status=409):
    return MetaAdsConnectionServiceError(status, code, message)


class MetaAdsConnectionService:
    def __init__(self, db, *, settings: Settings | None = None, repository=None, token_exchange_client=None):
        self.db = db
        self.settings = settings or get_settings()
        self.repository = repository or MetaAdsLiveRepository(db)
        self.token_exchange_client = token_exchange_client

    def blockers(self):
        s = self.settings
        blockers = []
        if not s.meta_connections_enabled:
            blockers.append("feature_disabled")
        if not s.meta_live_oauth_enabled:
            blockers.append("live_oauth_disabled")
        if not s.meta_token_storage_enabled:
            blockers.append("token_storage_disabled")
        if s.meta_ads_api_version not in SUPPORTED_ADS_VERSIONS:
            blockers.append("unsupported_api_version")
        if not (s.meta_ads_app_id and s.meta_ads_app_secret and s.meta_token_encryption_key
                and self._callback_url(s.meta_ads_oauth_redirect_uri)
                and urlparse(s.meta_ads_oauth_redirect_uri).path.rstrip("/") == f"{s.api_v1_prefix}/integrations/meta-ads/oauth/callback"
                and self._callback_url(s.meta_ads_oauth_frontend_callback_url)):
            blockers.append("missing_required_configuration")
        if s.meta_token_encryption_key:
            try:
                Fernet(s.meta_token_encryption_key.encode())
            except (ValueError, TypeError):
                blockers.append("invalid_encryption_configuration")
        return blockers

    @staticmethod
    def _callback_url(value):
        if not value:
            return False
        u = urlparse(value)
        return u.scheme == "https" and bool(u.hostname) and not u.username and not u.password and not u.query and not u.fragment and "instagram" not in u.path.lower()

    def _ensure_ready(self):
        blockers = self.blockers()
        if blockers:
            raise error(blockers[0], "Meta Ads connection is not available. Complete Ads setup first.",
                        403 if blockers[0] in {"feature_disabled", "live_oauth_disabled"} else 409)

    def get_status(self, workspace_id, user_id=None):
        connection = self.repository.get_current(workspace_id) if self.settings.meta_connections_enabled else None
        blockers = self.blockers()
        status = connection.connection_status if connection else "NOT_CONNECTED"
        configured = not any(x in blockers for x in {"missing_required_configuration", "unsupported_api_version", "invalid_encryption_configuration"})
        return MetaAdsConnectionStatusResponse(
            workspace_id=workspace_id, connection_status=status, connected=status == "CONNECTED",
            live_oauth_enabled=self.settings.meta_live_oauth_enabled,
            connections_enabled=self.settings.meta_connections_enabled,
            token_storage_enabled=self.settings.meta_token_storage_enabled,
            sync_enabled=self.settings.meta_sync_enabled, configured=configured,
            reason=blockers[0] if blockers else None, blockers=blockers,
            message="Meta Ads setup is required." if blockers else "Meta Ads read-only connection is available.",
            implemented=True, account_selection_required=status == "CONNECTED" and not connection.external_ad_account_id,
            can_connect=not blockers, can_sync=not blockers and self.settings.meta_sync_enabled and status == "CONNECTED" and bool(connection.external_ad_account_id),
            account_name=connection.account_name if connection else None,
            currency=connection.currency if connection else None, timezone=connection.timezone if connection else None,
            token_expires_at=connection.token_expires_at if connection else None,
            connected_at=connection.connected_at if connection else None,
            disconnected_at=connection.disconnected_at if connection else None,
            last_synced_at=connection.last_synced_at if connection else None,
            last_sync_attempt_at=connection.last_sync_attempt_at if connection else None,
            last_error_code=connection.last_error_code if connection else None,
            last_error_message=connection.last_error_message if connection else None)

    def start_oauth(self, workspace_id, user_id):
        self._ensure_ready()
        self.repository.lock_workspace(workspace_id)
        c = self.repository.get_or_create(workspace_id)
        c.generation = str(uuid4())
        c.connection_status = "CONNECTING"
        c.encrypted_access_token = None
        c.external_ad_account_id = c.account_name = c.currency = c.timezone = None
        c.token_fingerprint = c.token_expires_at = None
        c.connected_by_user_id = user_id
        state, expires = self.repository.issue_state(workspace_id, user_id, c.generation)
        self.repository.audit(workspace_id, user_id, "meta_ads_connect_started", c)
        self.db.commit()
        s = self.settings
        return MetaAdsOAuthStartResponse(**self.get_status(workspace_id).model_dump(),
            authorization_url=build_meta_oauth_authorization_url(
                authorize_url=f"https://www.facebook.com/{s.meta_ads_api_version}/dialog/oauth",
                app_id=s.meta_ads_app_id, redirect_uri=s.meta_ads_oauth_redirect_uri,
                state=state, scopes=("ads_read",), config_id=s.meta_ads_login_config_id), state_expires_at=expires)

    def complete_callback(self, workspace_id, user_id, *, state, code):
        self._ensure_ready()
        self.repository.lock_workspace(workspace_id)
        generation = self.repository.consume_state(workspace_id, user_id, state)
        self.db.commit()  # Consume once, durably, BEFORE any provider call.
        if generation is None:
            raise error("invalid_state", "Invalid or expired Meta Ads authorization state.", 400)
        s = self.settings
        client = self.token_exchange_client or MetaLiveOAuthClient(app_id=s.meta_ads_app_id,
            app_secret=s.meta_ads_app_secret, api_version=s.meta_ads_api_version)
        try:
            token = client.exchange_code_for_token(code=code, redirect_uri=s.meta_ads_oauth_redirect_uri)
            if "ads_read" not in token.scopes:
                raise MetaLiveOAuthClientError("Meta Ads permission is missing.")
            encrypted = encrypt_token(token.access_token, s.meta_token_encryption_key)
        except (MetaLiveOAuthClientError, MetaTokenCryptoError):
            self.repository.lock_workspace(workspace_id)
            c = self.repository.get_current(workspace_id)
            if c and c.generation == generation:
                c.connection_status = "NEEDS_REAUTH"
                c.last_error_code = "oauth_callback_failed"
                c.last_error_message = "Meta Ads authorization failed. Reconnect and grant ads_read."
                self.repository.audit(workspace_id, user_id, "meta_ads_connect_failed", c)
                self.db.commit()
            else:
                self.db.rollback()
            raise error("oauth_callback_failed", "Meta Ads authorization failed. Reconnect and grant ads_read.") from None
        self.repository.lock_workspace(workspace_id)
        c = self.repository.get_current(workspace_id)
        if not c or c.generation != generation or c.connection_status != "CONNECTING":
            self.db.rollback()
            raise error("connection_changed", "Meta Ads connection changed. Start authorization again.")
        c.encrypted_access_token = encrypted
        c.token_expires_at = token.expires_at
        c.scopes = "ads_read"
        c.connection_status = "CONNECTED"
        c.connected_at = datetime.now(UTC)
        c.disconnected_at = None
        c.last_error_code = c.last_error_message = None
        self.repository.audit(workspace_id, user_id, "meta_ads_connect_succeeded", c)
        self.db.commit()
        return MetaAdsOAuthCallbackResponse(**self.get_status(workspace_id).model_dump(), token_stored=True)

    def callback_redirect(self, *, code=None, state=None, denied=False):
        self._ensure_ready()
        params = {"error": "access_denied"} if denied or not code or not state else {"code": code, "state": state}
        return self.settings.meta_ads_oauth_frontend_callback_url + "?" + urlencode(params)

    def disconnect(self, workspace_id, user_id):
        if not self.settings.meta_connections_enabled:
            raise error("feature_disabled", "Meta Ads connections are disabled.", 403)
        self.repository.lock_workspace(workspace_id)
        c = self.repository.get_or_create(workspace_id)
        c.generation = str(uuid4())
        c.connection_status = "DISCONNECTED"
        c.encrypted_access_token = c.token_fingerprint = c.token_expires_at = c.scopes = None
        c.external_ad_account_id = c.account_name = c.currency = c.timezone = None
        c.disconnected_at = datetime.now(UTC)
        c.last_error_code = c.last_error_message = None
        self.repository.invalidate_states(workspace_id)
        self.repository.audit(workspace_id, user_id, "meta_ads_disconnected", c)
        self.db.commit()
        return MetaAdsDisconnectResponse(**self.get_status(workspace_id).model_dump())
