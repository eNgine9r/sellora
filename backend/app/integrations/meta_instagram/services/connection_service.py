from datetime import UTC, datetime
from uuid import UUID
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.integrations.meta_instagram.client import MetaInstagramClient, MetaInstagramOAuthClient, MetaInstagramOAuthClientProtocol, MetaTokenResult
from app.integrations.meta_instagram.config import PROFESSIONAL_ACCOUNT_TYPES, REQUIRED_BASIC_PERMISSION, REQUIRED_MESSAGING_PERMISSION, WEBHOOK_SUBSCRIPTIONS
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
        connection = self.repo.get_active(oauth_state.workspace_id) or self.repo.create(InstagramConnection(workspace_id=oauth_state.workspace_id, created_by=oauth_state.user_id))
        connection.meta_app_id = settings.meta_app_id
        connection.instagram_account_id = token.user_id
        connection.granted_permissions = token.granted_permissions or []
        try:
            profile = await client.inspect_account(access_token=token.access_token, token_user_id=token.user_id)
        except MetaInstagramError as exc:
            connection.status = InstagramConnectionStatus.FAILED.value
            connection.last_error_code = exc.code
            connection.last_error_message = exc.message[:300]
            oauth_state.consumed_at = datetime.now(UTC)
            raise
        connection.instagram_account_id = profile.instagram_account_id
        connection.instagram_username = profile.username
        connection.instagram_account_type = profile.account_type
        connection.granted_permissions = profile.granted_permissions
        connection.subscribed_webhook_fields = []
        connection.token_expires_at = token.expires_at or profile.token_expires_at
        connection.token_last_validated_at = datetime.now(UTC)
        connection.updated_by = oauth_state.user_id
        normalized_account_type = (profile.account_type or "").upper()
        if not normalized_account_type:
            connection.status = InstagramConnectionStatus.FAILED.value
            connection.last_error_code = "META_ACCOUNT_TYPE_UNVERIFIED"
            connection.last_error_message = "Instagram account type could not be verified."
            oauth_state.consumed_at = datetime.now(UTC)
            raise MetaInstagramError("META_ACCOUNT_TYPE_UNVERIFIED", "Instagram account type could not be verified.", 400)
        if normalized_account_type not in PROFESSIONAL_ACCOUNT_TYPES:
            connection.status = InstagramConnectionStatus.FAILED.value
            connection.last_error_code = "META_ACCOUNT_NOT_PROFESSIONAL"
            connection.last_error_message = "Instagram account must be Business or Creator."
            oauth_state.consumed_at = datetime.now(UTC)
            raise MetaInstagramError("META_ACCOUNT_NOT_PROFESSIONAL", "Instagram account must be Business or Creator.", 400)
        if not self._permissions_ok(profile.granted_permissions):
            connection.status = InstagramConnectionStatus.PERMISSION_MISSING.value
            connection.last_error_code = "META_PERMISSION_MISSING"
            connection.last_error_message = "Required Instagram messaging permissions are missing."
            oauth_state.consumed_at = datetime.now(UTC)
            return connection
        ciphertext, nonce, version = encrypt_instagram_token(token.access_token)
        connection.access_token_ciphertext = ciphertext
        connection.access_token_nonce = nonce
        connection.access_token_key_version = version
        await self._activate_webhook_subscription(connection, token.access_token)
        if connection.status == InstagramConnectionStatus.CONNECTED.value:
            connection.connected_at = datetime.now(UTC)
        oauth_state.consumed_at = datetime.now(UTC)
        return connection
    async def validate(self, workspace_id: UUID) -> tuple[InstagramConnection | None, bool]:
        connection = self.repo.get_active(workspace_id)
        if not connection: return None, False
        if not connection.access_token_ciphertext:
            connection.status = InstagramConnectionStatus.RECONNECT_REQUIRED.value; return connection, False
        token = decrypt_instagram_token(connection.access_token_ciphertext)
        profile = await self._oauth_client().inspect_account(access_token=token, token_user_id=connection.instagram_account_id)
        permission_ok = self._permissions_ok(profile.granted_permissions)
        professional = (profile.account_type or "").upper() in PROFESSIONAL_ACCOUNT_TYPES
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
            await self._activate_webhook_subscription(connection, token)
        return connection, permission_ok and professional and connection.status == InstagramConnectionStatus.CONNECTED.value
    async def subscribe_webhooks(self, workspace_id: UUID) -> InstagramConnection:
        connection = self.repo.get_active(workspace_id)
        if not connection: raise MetaInstagramError("META_CONNECTION_NOT_FOUND", "Instagram connection not found.", 404)
        if not connection.access_token_ciphertext or not connection.instagram_account_id:
            connection.status = InstagramConnectionStatus.RECONNECT_REQUIRED.value
            raise MetaInstagramError("META_RECONNECT_REQUIRED", "Reconnect Instagram before activating webhooks.", 409)
        await self._activate_webhook_subscription(connection, decrypt_instagram_token(connection.access_token_ciphertext))
        return connection
    async def refresh_webhook_status(self, workspace_id: UUID) -> InstagramConnection | None:
        connection = self.repo.get_active(workspace_id)
        if not connection or not connection.access_token_ciphertext or not connection.instagram_account_id:
            return connection
        token = decrypt_instagram_token(connection.access_token_ciphertext)
        verified = await self._subscription_client(token).get_webhook_subscription(connection.instagram_account_id)
        self._apply_subscription_check(connection, verified.subscribed_fields)
        return connection
    async def unsubscribe_webhooks(self, workspace_id: UUID) -> InstagramConnection:
        connection = self.repo.get_active(workspace_id)
        if not connection: raise MetaInstagramError("META_CONNECTION_NOT_FOUND", "Instagram connection not found.", 404)
        if connection.access_token_ciphertext and connection.instagram_account_id:
            await self._subscription_client(decrypt_instagram_token(connection.access_token_ciphertext)).unsubscribe_webhooks(connection.instagram_account_id)
        connection.subscribed_webhook_fields = []
        connection.status = InstagramConnectionStatus.WEBHOOK_INACTIVE.value if connection.access_token_ciphertext else InstagramConnectionStatus.RECONNECT_REQUIRED.value
        return connection
    async def disconnect(self, workspace_id: UUID, user_id: UUID) -> InstagramConnection:
        connection = self.repo.get_active(workspace_id)
        if not connection: raise MetaInstagramError("META_CONNECTION_NOT_FOUND", "Instagram connection not found.", 404)
        if connection.access_token_ciphertext and connection.instagram_account_id:
            try:
                await self._subscription_client(decrypt_instagram_token(connection.access_token_ciphertext)).unsubscribe_webhooks(connection.instagram_account_id)
                connection.subscribed_webhook_fields = []
            except MetaInstagramError as exc:
                connection.last_error_code = exc.code
                connection.last_error_message = exc.message[:300]
        connection.status = InstagramConnectionStatus.DISCONNECTED.value; connection.disconnected_at = datetime.now(UTC); connection.access_token_ciphertext = None; connection.access_token_nonce = None; connection.updated_by = user_id
        return connection
    def _permissions_ok(self, granted_permissions: list[str]) -> bool:
        return REQUIRED_BASIC_PERMISSION in granted_permissions and REQUIRED_MESSAGING_PERMISSION in granted_permissions
    def _oauth_client(self) -> MetaInstagramOAuthClientProtocol:
        if self.oauth_client: return self.oauth_client
        s = get_settings()
        if not s.meta_app_id or not s.meta_app_secret:
            raise MetaInstagramError("META_CONFIGURATION_MISSING", "Meta app credentials are not configured.", 409)
        return MetaInstagramOAuthClient(app_id=s.meta_app_id, app_secret=s.meta_app_secret, token_url=s.meta_instagram_oauth_token_url, graph_base_url=s.meta_graph_api_base_url, graph_version=s.meta_graph_api_version)
    def _subscription_client(self, access_token: str) -> MetaInstagramClient:
        s = get_settings()
        return MetaInstagramClient(s.meta_graph_api_base_url, s.meta_graph_api_version, access_token)
    async def _maybe_long_lived(self, client: MetaInstagramOAuthClientProtocol, token: MetaTokenResult) -> MetaTokenResult:
        return await client.exchange_long_lived(access_token=token.access_token)
    async def _activate_webhook_subscription(self, connection: InstagramConnection, access_token: str) -> None:
        if not connection.instagram_account_id:
            connection.status = InstagramConnectionStatus.WEBHOOK_INACTIVE.value
            connection.last_error_code = "META_ACCOUNT_IDENTITY_MISSING"
            connection.last_error_message = "Instagram account identity is missing."
            return
        client = self._subscription_client(access_token)
        try:
            result = await client.subscribe_webhooks(connection.instagram_account_id, WEBHOOK_SUBSCRIPTIONS)
            if not result.success:
                self._mark_webhook_inactive(connection, "META_WEBHOOK_SUBSCRIPTION_FAILED", "Meta webhook subscription failed.")
                return
            verified = await client.get_webhook_subscription(connection.instagram_account_id)
        except MetaInstagramError as exc:
            self._mark_webhook_inactive(connection, exc.code if exc.code != "META_PROVIDER_RATE_LIMITED" else exc.code, exc.message)
            return
        self._apply_subscription_check(connection, verified.subscribed_fields)
    def _apply_subscription_check(self, connection: InstagramConnection, confirmed_fields: list[str]) -> None:
        confirmed = [field for field in WEBHOOK_SUBSCRIPTIONS if field in set(confirmed_fields)]
        missing = [field for field in WEBHOOK_SUBSCRIPTIONS if field not in set(confirmed_fields)]
        connection.subscribed_webhook_fields = confirmed
        if missing:
            self._mark_webhook_inactive(connection, "META_WEBHOOK_SUBSCRIPTION_INCOMPLETE", "Meta webhook subscription is missing required fields.")
            return
        connection.status = InstagramConnectionStatus.CONNECTED.value
        connection.last_error_code = None
        connection.last_error_message = None
    def _mark_webhook_inactive(self, connection: InstagramConnection, code: str, message: str) -> None:
        connection.subscribed_webhook_fields = []
        connection.status = InstagramConnectionStatus.WEBHOOK_INACTIVE.value
        connection.last_error_code = code
        connection.last_error_message = message[:300]
