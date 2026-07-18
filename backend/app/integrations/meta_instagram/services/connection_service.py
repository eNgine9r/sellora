from datetime import UTC, datetime
from uuid import UUID
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.integrations.meta_instagram.client import MetaInstagramOAuthClient, MetaInstagramOAuthClientProtocol, MetaTokenResult
from app.integrations.meta_instagram.config import PROFESSIONAL_ACCOUNT_TYPES, REQUIRED_MESSAGING_PERMISSION, WEBHOOK_SUBSCRIPTIONS
from app.integrations.meta_instagram.crypto import decrypt_instagram_token, encrypt_instagram_token
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.repositories.connection_repository import InstagramConnectionRepository
from app.integrations.meta_instagram.services.oauth_service import InstagramOAuthService
from app.models.meta_instagram import InstagramConnection, InstagramConnectionStatus

class InstagramConnectionService:
    def __init__(self, db: Session, oauth_client: MetaInstagramOAuthClientProtocol | None = None) -> None:
        self.db = db; self.repo = InstagramConnectionRepository(db); self.oauth_client = oauth_client
    def start_connect(self, workspace_id: UUID, user_id: UUID): return InstagramOAuthService(self.db).start(workspace_id, user_id)
    def status(self, workspace_id: UUID) -> InstagramConnection | None: return self.repo.get_active(workspace_id)
    async def complete_callback(self, state: str, code: str) -> InstagramConnection:
        oauth_state = InstagramOAuthService(self.db).validate_state(state)
        if not code:
            raise MetaInstagramError("META_OAUTH_STATE_INVALID", "OAuth code is required.")
        client = self._oauth_client()
        settings = get_settings()
        token = await client.exchange_code(code=code, redirect_uri=oauth_state.redirect_uri)
        token = await self._maybe_long_lived(client, token)
        profile = await client.inspect_account(access_token=token.access_token)
        connection = self.repo.get_active(oauth_state.workspace_id) or self.repo.create(InstagramConnection(workspace_id=oauth_state.workspace_id, created_by=oauth_state.user_id))
        connection.meta_app_id = settings.meta_app_id
        connection.instagram_account_id = profile.instagram_account_id
        connection.instagram_username = profile.username
        connection.instagram_account_type = profile.account_type
        connection.granted_permissions = profile.granted_permissions
        connection.subscribed_webhook_fields = WEBHOOK_SUBSCRIPTIONS
        connection.token_expires_at = token.expires_at or profile.token_expires_at
        connection.token_last_validated_at = datetime.now(UTC)
        connection.updated_by = oauth_state.user_id
        if REQUIRED_MESSAGING_PERMISSION not in profile.granted_permissions:
            connection.status = InstagramConnectionStatus.PERMISSION_MISSING.value
            oauth_state.consumed_at = datetime.now(UTC)
            return connection
        if profile.account_type not in PROFESSIONAL_ACCOUNT_TYPES:
            connection.status = InstagramConnectionStatus.FAILED.value
            oauth_state.consumed_at = datetime.now(UTC)
            raise MetaInstagramError("META_ACCOUNT_NOT_PROFESSIONAL", "Instagram account must be Business or Creator.", 400)
        ciphertext, nonce, version = encrypt_instagram_token(token.access_token)
        connection.access_token_ciphertext = ciphertext
        connection.access_token_nonce = nonce
        connection.access_token_key_version = version
        connection.status = InstagramConnectionStatus.CONNECTED.value
        connection.connected_at = datetime.now(UTC)
        oauth_state.consumed_at = datetime.now(UTC)
        return connection
    async def validate(self, workspace_id: UUID) -> tuple[InstagramConnection | None, bool]:
        connection = self.repo.get_active(workspace_id)
        if not connection: return None, False
        if not connection.access_token_ciphertext:
            connection.status = InstagramConnectionStatus.RECONNECT_REQUIRED.value; return connection, False
        token = decrypt_instagram_token(connection.access_token_ciphertext)
        profile = await self._oauth_client().inspect_account(access_token=token)
        permission_ok = REQUIRED_MESSAGING_PERMISSION in profile.granted_permissions
        professional = profile.account_type in PROFESSIONAL_ACCOUNT_TYPES
        connection.instagram_account_id = profile.instagram_account_id
        connection.instagram_username = profile.username
        connection.instagram_account_type = profile.account_type
        connection.granted_permissions = profile.granted_permissions
        connection.token_last_validated_at = datetime.now(UTC)
        if connection.token_expires_at and connection.token_expires_at < datetime.now(UTC):
            connection.status = InstagramConnectionStatus.TOKEN_EXPIRED.value
        elif not professional:
            connection.status = InstagramConnectionStatus.FAILED.value
        elif not permission_ok:
            connection.status = InstagramConnectionStatus.PERMISSION_MISSING.value
        else:
            ciphertext, nonce, version = encrypt_instagram_token(token)
            connection.access_token_ciphertext = ciphertext
            connection.access_token_nonce = nonce
            connection.access_token_key_version = version
            connection.status = InstagramConnectionStatus.CONNECTED.value
        return connection, permission_ok and professional and connection.status == InstagramConnectionStatus.CONNECTED.value
    def disconnect(self, workspace_id: UUID, user_id: UUID) -> InstagramConnection:
        connection = self.repo.get_active(workspace_id)
        if not connection: raise MetaInstagramError("META_CONNECTION_NOT_FOUND", "Instagram connection not found.", 404)
        connection.status = InstagramConnectionStatus.DISCONNECTED.value; connection.disconnected_at = datetime.now(UTC); connection.access_token_ciphertext = None; connection.access_token_nonce = None; connection.updated_by = user_id
        return connection
    def _oauth_client(self) -> MetaInstagramOAuthClientProtocol:
        if self.oauth_client: return self.oauth_client
        s = get_settings()
        if not s.meta_app_id or not s.meta_app_secret:
            raise MetaInstagramError("META_CONFIGURATION_MISSING", "Meta app credentials are not configured.", 409)
        return MetaInstagramOAuthClient(app_id=s.meta_app_id, app_secret=s.meta_app_secret, token_url=s.meta_instagram_oauth_token_url, graph_base_url=s.meta_graph_api_base_url, graph_version=s.meta_graph_api_version)
    async def _maybe_long_lived(self, client: MetaInstagramOAuthClientProtocol, token: MetaTokenResult) -> MetaTokenResult:
        return await client.exchange_long_lived(access_token=token.access_token)
