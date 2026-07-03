from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.integrations.meta_ads.audit_stub import build_meta_ads_live_audit_event
from app.integrations.meta_ads.live_oauth_client import (
    DisabledMetaLiveOAuthClient,
    MetaLiveOAuthClientError,
    MetaLiveOAuthClientProtocol,
    build_meta_oauth_authorization_url,
)
from app.integrations.meta_ads.oauth_state import MetaOAuthStateError, generate_live_oauth_state, validate_live_oauth_state
from app.integrations.meta_ads.token_crypto import MetaTokenCryptoError, encrypt_token
from app.integrations.meta_ads.token_safety import mask_token, safe_token_fingerprint
from app.models.meta_ad_connection import MetaAdConnection, MetaAdConnectionStatus
from app.repositories.meta_ads_connection_repository import MetaAdsConnectionRepository
from app.schemas.meta_ads_connection import (
    MetaAdsConnectionStatusResponse,
    MetaAdsDisconnectResponse,
    MetaAdsOAuthCallbackResponse,
    MetaAdsOAuthStartResponse,
)


@dataclass(frozen=True)
class MetaAdsConnectionServiceError(Exception):
    status_code: int
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


class MetaAdsConnectionService:
    def __init__(
        self,
        db: Session,
        *,
        settings: Settings | None = None,
        repository: MetaAdsConnectionRepository | None = None,
        token_exchange_client: MetaLiveOAuthClientProtocol | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.repository = repository or MetaAdsConnectionRepository(db)
        self.token_exchange_client = token_exchange_client or DisabledMetaLiveOAuthClient()

    def get_status(self, workspace_id: UUID, user_id: UUID | None = None) -> MetaAdsConnectionStatusResponse:
        connection = self.repository.get_current(workspace_id) if self.settings.meta_connections_enabled else None
        audit_event = build_meta_ads_live_audit_event(
            event="meta_ads_status_viewed",
            workspace_id=workspace_id,
            user_id=user_id,
            outcome="viewed",
        )
        return self._status_response(workspace_id, connection, audit_event=asdict(audit_event))

    def start_oauth(self, workspace_id: UUID, user_id: UUID) -> MetaAdsOAuthStartResponse:
        self._ensure_connections_enabled()
        self._ensure_live_oauth_enabled()
        self._ensure_oauth_configured()
        state, payload = generate_live_oauth_state(workspace_id, user_id)
        connection = self.repository.get_or_create(workspace_id)
        connection.connection_status = MetaAdConnectionStatus.CONNECTING.value
        connection.connected_by_user_id = user_id
        self.db.commit()
        audit_event = build_meta_ads_live_audit_event(
            event="meta_ads_connect_started",
            workspace_id=workspace_id,
            user_id=user_id,
            outcome="started",
        )
        response = self._status_response(workspace_id, connection, audit_event=asdict(audit_event))
        return MetaAdsOAuthStartResponse(
            **response.model_dump(),
            authorization_url=build_meta_oauth_authorization_url(
                authorize_url=self.settings.meta_oauth_authorize_url or "https://meta-oauth.local/authorize",
                app_id=self.settings.meta_app_id or "",
                redirect_uri=self.settings.meta_oauth_redirect_uri or "",
                state=state,
                scopes=("ads_read",),
            ),
            state_expires_at=payload.expires_at,
        )

    def complete_callback(self, workspace_id: UUID, user_id: UUID, *, state: str, code: str) -> MetaAdsOAuthCallbackResponse:
        self._ensure_connections_enabled()
        self._ensure_live_oauth_enabled()
        validate_live_oauth_state(state, workspace_id, user_id)
        if not self.settings.meta_token_storage_enabled:
            raise MetaAdsConnectionServiceError(409, "token_storage_disabled", "Meta token storage is disabled.")
        if not self.settings.meta_token_encryption_key:
            raise MetaAdsConnectionServiceError(409, "missing_encryption_key", "Meta token encryption key is not configured.")
        if not self.settings.meta_oauth_redirect_uri:
            raise MetaAdsConnectionServiceError(409, "missing_required_configuration", "Meta OAuth redirect URI is not configured.")
        try:
            token_result = self.token_exchange_client.exchange_code_for_token(code=code, redirect_uri=self.settings.meta_oauth_redirect_uri)
            encrypted_token = encrypt_token(token_result.access_token, self.settings.meta_token_encryption_key)
        except (MetaLiveOAuthClientError, MetaTokenCryptoError) as exc:
            connection = self.repository.get_or_create(workspace_id)
            connection.connection_status = MetaAdConnectionStatus.ERROR.value
            connection.last_error_code = "oauth_callback_failed"
            connection.last_error_message = "Meta OAuth callback failed safely."
            self.db.commit()
            build_meta_ads_live_audit_event(event="meta_ads_connect_failed", workspace_id=workspace_id, user_id=user_id, outcome="failed")
            raise MetaAdsConnectionServiceError(409, "oauth_callback_failed", str(exc)) from exc
        connection = self.repository.get_or_create(workspace_id)
        connection.connection_status = MetaAdConnectionStatus.CONNECTED.value
        connection.encrypted_access_token = encrypted_token
        connection.token_fingerprint = safe_token_fingerprint(token_result.access_token)
        connection.token_expires_at = token_result.expires_at
        connection.scopes = ",".join(token_result.scopes)
        connection.connected_by_user_id = user_id
        connection.connected_at = datetime.now(UTC)
        connection.disconnected_at = None
        connection.last_error_code = None
        connection.last_error_message = None
        self.db.commit()
        audit_event = build_meta_ads_live_audit_event(
            event="meta_ads_connect_succeeded",
            workspace_id=workspace_id,
            user_id=user_id,
            outcome="succeeded",
            payload={"token_fingerprint": connection.token_fingerprint},
        )
        response = self._status_response(workspace_id, connection, audit_event=asdict(audit_event))
        return MetaAdsOAuthCallbackResponse(**response.model_dump(), token_stored=True)

    def disconnect(self, workspace_id: UUID, user_id: UUID) -> MetaAdsDisconnectResponse:
        self._ensure_connections_enabled()
        connection = self.repository.get_or_create(workspace_id)
        connection.connection_status = MetaAdConnectionStatus.DISCONNECTED.value
        connection.encrypted_access_token = None
        connection.token_fingerprint = None
        connection.token_expires_at = None
        connection.disconnected_at = datetime.now(UTC)
        self.db.commit()
        audit_event = build_meta_ads_live_audit_event(
            event="meta_ads_disconnected",
            workspace_id=workspace_id,
            user_id=user_id,
            outcome="disconnected",
        )
        response = self._status_response(workspace_id, connection, audit_event=asdict(audit_event))
        return MetaAdsDisconnectResponse(**response.model_dump(), disconnected=True)

    def _status_response(self, workspace_id: UUID, connection: MetaAdConnection | None, audit_event: dict[str, object] | None = None) -> MetaAdsConnectionStatusResponse:
        configured = self._is_oauth_configured()
        reason = None
        message = "Meta Ads connection is not available yet."
        if not self.settings.meta_connections_enabled:
            reason = "feature_disabled"
            message = "Meta Ads connection foundation is disabled."
        elif not self.settings.meta_live_oauth_enabled:
            reason = "live_oauth_disabled"
            message = "Meta Ads live OAuth is disabled."
        elif not configured:
            reason = "missing_required_configuration"
            message = "Meta Ads connection is not available yet."
        status = MetaAdConnectionStatus.NOT_CONNECTED
        if connection is not None:
            status = MetaAdConnectionStatus(connection.connection_status)
        return MetaAdsConnectionStatusResponse(
            workspace_id=workspace_id,
            connection_status=status,
            connected=status == MetaAdConnectionStatus.CONNECTED,
            live_oauth_enabled=self.settings.meta_live_oauth_enabled,
            connections_enabled=self.settings.meta_connections_enabled,
            token_storage_enabled=self.settings.meta_token_storage_enabled,
            sync_enabled=self.settings.meta_sync_enabled,
            configured=configured,
            reason=reason,
            message=message,
            account_name=connection.account_name if connection else None,
            currency=connection.currency if connection else None,
            timezone=connection.timezone if connection else None,
            external_ad_account_id_masked=mask_token(connection.external_ad_account_id) if connection and connection.external_ad_account_id else None,
            token_fingerprint=connection.token_fingerprint if connection else None,
            token_expires_at=connection.token_expires_at if connection else None,
            connected_at=connection.connected_at if connection else None,
            disconnected_at=connection.disconnected_at if connection else None,
            last_synced_at=connection.last_synced_at if connection else None,
            audit_event=audit_event,
        )

    def _is_oauth_configured(self) -> bool:
        return bool(self.settings.meta_app_id and self.settings.meta_oauth_redirect_uri and self.settings.meta_oauth_authorize_url)

    def _ensure_connections_enabled(self) -> None:
        if not self.settings.meta_connections_enabled:
            raise MetaAdsConnectionServiceError(403, "feature_disabled", "Meta Ads connection foundation is disabled.")

    def _ensure_live_oauth_enabled(self) -> None:
        if not self.settings.meta_live_oauth_enabled:
            raise MetaAdsConnectionServiceError(403, "live_oauth_disabled", "Meta Ads live OAuth is disabled.")

    def _ensure_oauth_configured(self) -> None:
        if not self._is_oauth_configured():
            raise MetaAdsConnectionServiceError(409, "missing_required_configuration", "Meta Ads connection is not available yet.")
