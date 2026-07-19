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
        self.db = db
        self.repo = InstagramConnectionRepository(db)
        self.oauth_client = oauth_client

    def start_connect(self, workspace_id: UUID, user_id: UUID):
        return InstagramOAuthService(self.db).start(workspace_id, user_id)

    def status(self, workspace_id: UUID) -> InstagramConnection | None:
        return self.repo.get_active(workspace_id)

    async def complete_callback(self, state: str, code: str) -> InstagramConnection:
        oauth_state = InstagramOAuthService(self.db).validate_state(state)
        if not code:
            raise MetaInstagramError("META_OAUTH_STATE_INVALID", "OAuth code is required.")

        existing = self.repo.get_active(oauth_state.workspace_id)
        existing_operational = self._is_operational(existing)
        client = self._oauth_client()
        settings = get_settings()
        token = await client.exchange_code(code=code, redirect_uri=oauth_state.redirect_uri)
        token = await self._maybe_long_lived(client, token)

        try:
            profile = await client.inspect_account(access_token=token.access_token, token_user_id=token.user_id)
        except MetaInstagramError as exc:
            oauth_state.consumed_at = datetime.now(UTC)
            if not existing_operational:
                self._persist_callback_failure(
                    existing,
                    oauth_state.workspace_id,
                    oauth_state.user_id,
                    settings.meta_app_id,
                    exc.code,
                    exc.message,
                )
            raise

        conflict = self.repo.get_connected_in_other_workspace(
            profile.instagram_account_id,
            oauth_state.workspace_id,
        )
        if conflict:
            oauth_state.consumed_at = datetime.now(UTC)
            if not existing_operational:
                self._persist_callback_failure(
                    existing,
                    oauth_state.workspace_id,
                    oauth_state.user_id,
                    settings.meta_app_id,
                    "META_ACCOUNT_ALREADY_CONNECTED",
                    "This Instagram account is already connected to another Sellora workspace.",
                    profile=profile,
                )
            raise MetaInstagramError(
                "META_ACCOUNT_ALREADY_CONNECTED",
                "This Instagram account is already connected to another Sellora workspace.",
                409,
            )

        normalized_account_type = (profile.account_type or "").upper()
        if not normalized_account_type:
            oauth_state.consumed_at = datetime.now(UTC)
            if not existing_operational:
                self._persist_callback_failure(
                    existing,
                    oauth_state.workspace_id,
                    oauth_state.user_id,
                    settings.meta_app_id,
                    "META_ACCOUNT_TYPE_UNVERIFIED",
                    "Instagram account type could not be verified.",
                    profile=profile,
                )
            raise MetaInstagramError("META_ACCOUNT_TYPE_UNVERIFIED", "Instagram account type could not be verified.", 400)
        if normalized_account_type not in PROFESSIONAL_ACCOUNT_TYPES:
            oauth_state.consumed_at = datetime.now(UTC)
            if not existing_operational:
                self._persist_callback_failure(
                    existing,
                    oauth_state.workspace_id,
                    oauth_state.user_id,
                    settings.meta_app_id,
                    "META_ACCOUNT_NOT_PROFESSIONAL",
                    "Instagram account must be Business or Creator.",
                    profile=profile,
                )
            raise MetaInstagramError("META_ACCOUNT_NOT_PROFESSIONAL", "Instagram account must be Business or Creator.", 400)
        if not self._permissions_ok(profile.granted_permissions):
            oauth_state.consumed_at = datetime.now(UTC)
            if existing_operational:
                raise MetaInstagramError(
                    "META_PERMISSION_MISSING",
                    "Required Instagram messaging permissions are missing.",
                    400,
                )
            connection = existing or self.repo.create(
                InstagramConnection(workspace_id=oauth_state.workspace_id, created_by=oauth_state.user_id)
            )
            self._apply_profile(connection, profile)
            connection.meta_app_id = settings.meta_app_id
            connection.status = InstagramConnectionStatus.PERMISSION_MISSING.value
            connection.last_error_code = "META_PERMISSION_MISSING"
            connection.last_error_message = "Required Instagram messaging permissions are missing."
            connection.access_token_ciphertext = None
            connection.access_token_nonce = None
            connection.access_token_key_version = None
            connection.updated_by = oauth_state.user_id
            return connection

        candidate = InstagramConnection(
            workspace_id=oauth_state.workspace_id,
            created_by=oauth_state.user_id,
            updated_by=oauth_state.user_id,
        )
        candidate.meta_app_id = settings.meta_app_id
        self._apply_profile(candidate, profile)
        candidate.subscribed_webhook_fields = []
        candidate.token_expires_at = token.expires_at or profile.token_expires_at
        candidate.token_last_validated_at = datetime.now(UTC)
        ciphertext, nonce, version = encrypt_instagram_token(token.access_token)
        candidate.access_token_ciphertext = ciphertext
        candidate.access_token_nonce = nonce
        candidate.access_token_key_version = version
        await self._activate_webhook_subscription(candidate, token.access_token)

        if existing_operational and candidate.status != InstagramConnectionStatus.CONNECTED.value:
            oauth_state.consumed_at = datetime.now(UTC)
            raise MetaInstagramError(
                candidate.last_error_code or "META_WEBHOOK_SUBSCRIPTION_FAILED",
                candidate.last_error_message or "Meta webhook subscription failed.",
                409,
            )

        if candidate.status == InstagramConnectionStatus.CONNECTED.value:
            candidate.connected_at = datetime.now(UTC)
            candidate.disconnected_at = None

        if existing:
            self._copy_candidate(existing, candidate)
            connection = existing
        else:
            connection = self.repo.create(candidate)
        oauth_state.consumed_at = datetime.now(UTC)
        return connection

    async def validate(self, workspace_id: UUID) -> tuple[InstagramConnection | None, bool]:
        connection = self.repo.get_active(workspace_id)
        if not connection:
            return None, False
        if not connection.access_token_ciphertext:
            connection.status = InstagramConnectionStatus.RECONNECT_REQUIRED.value
            return connection, False
        token = decrypt_instagram_token(connection.access_token_ciphertext)
        profile = await self._oauth_client().inspect_account(access_token=token, token_user_id=connection.instagram_account_id)
        permission_ok = self._permissions_ok(profile.granted_permissions)
        professional = (profile.account_type or "").upper() in PROFESSIONAL_ACCOUNT_TYPES
        if connection.token_expires_at and connection.token_expires_at < datetime.now(UTC):
            connection.status = InstagramConnectionStatus.TOKEN_EXPIRED.value
            return connection, False
        if not professional:
            connection.status = InstagramConnectionStatus.FAILED.value
            return connection, False
        if not permission_ok:
            connection.status = InstagramConnectionStatus.PERMISSION_MISSING.value
            return connection, False
        conflict = self.repo.get_connected_in_other_workspace(profile.instagram_account_id, workspace_id)
        if conflict:
            connection.last_error_code = "META_ACCOUNT_ALREADY_CONNECTED"
            connection.last_error_message = "This Instagram account is already connected to another Sellora workspace."
            return connection, False

        connection.instagram_account_id = profile.instagram_account_id
        connection.instagram_username = profile.username
        connection.instagram_account_type = profile.account_type
        connection.granted_permissions = profile.granted_permissions
        connection.token_last_validated_at = datetime.now(UTC)
        ciphertext, nonce, version = encrypt_instagram_token(token)
        connection.access_token_ciphertext = ciphertext
        connection.access_token_nonce = nonce
        connection.access_token_key_version = version
        await self._activate_webhook_subscription(connection, token)
        return connection, connection.status == InstagramConnectionStatus.CONNECTED.value

    async def subscribe_webhooks(self, workspace_id: UUID) -> InstagramConnection:
        connection = self.repo.get_active(workspace_id)
        if not connection:
            raise MetaInstagramError("META_CONNECTION_NOT_FOUND", "Instagram connection not found.", 404)
        if not connection.access_token_ciphertext or not connection.instagram_account_id:
            connection.status = InstagramConnectionStatus.RECONNECT_REQUIRED.value
            raise MetaInstagramError("META_RECONNECT_REQUIRED", "Reconnect Instagram before activating webhooks.", 409)
        conflict = self.repo.get_connected_in_other_workspace(connection.instagram_account_id, workspace_id)
        if conflict:
            raise MetaInstagramError(
                "META_ACCOUNT_ALREADY_CONNECTED",
                "This Instagram account is already connected to another Sellora workspace.",
                409,
            )
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
        if not connection:
            raise MetaInstagramError("META_CONNECTION_NOT_FOUND", "Instagram connection not found.", 404)
        if connection.access_token_ciphertext and connection.instagram_account_id:
            await self._subscription_client(decrypt_instagram_token(connection.access_token_ciphertext)).unsubscribe_webhooks(connection.instagram_account_id)
        connection.subscribed_webhook_fields = []
        connection.status = InstagramConnectionStatus.WEBHOOK_INACTIVE.value if connection.access_token_ciphertext else InstagramConnectionStatus.RECONNECT_REQUIRED.value
        return connection

    async def disconnect(self, workspace_id: UUID, user_id: UUID) -> InstagramConnection:
        connection = self.repo.get_active(workspace_id)
        if not connection:
            raise MetaInstagramError("META_CONNECTION_NOT_FOUND", "Instagram connection not found.", 404)
        if connection.access_token_ciphertext and connection.instagram_account_id:
            try:
                await self._subscription_client(decrypt_instagram_token(connection.access_token_ciphertext)).unsubscribe_webhooks(connection.instagram_account_id)
                connection.subscribed_webhook_fields = []
            except MetaInstagramError as exc:
                connection.last_error_code = exc.code
                connection.last_error_message = exc.message[:300]
        connection.status = InstagramConnectionStatus.DISCONNECTED.value
        connection.disconnected_at = datetime.now(UTC)
        connection.access_token_ciphertext = None
        connection.access_token_nonce = None
        connection.access_token_key_version = None
        connection.updated_by = user_id
        return connection

    def _permissions_ok(self, granted_permissions: list[str]) -> bool:
        return REQUIRED_BASIC_PERMISSION in granted_permissions and REQUIRED_MESSAGING_PERMISSION in granted_permissions

    def _oauth_client(self) -> MetaInstagramOAuthClientProtocol:
        if self.oauth_client:
            return self.oauth_client
        settings = get_settings()
        if not settings.meta_app_id or not settings.meta_app_secret:
            raise MetaInstagramError("META_CONFIGURATION_MISSING", "Meta app credentials are not configured.", 409)
        return MetaInstagramOAuthClient(
            app_id=settings.meta_app_id,
            app_secret=settings.meta_app_secret,
            token_url=settings.meta_instagram_oauth_token_url,
            graph_base_url=settings.meta_graph_api_base_url,
            graph_version=settings.meta_graph_api_version,
        )

    def _subscription_client(self, access_token: str) -> MetaInstagramClient:
        settings = get_settings()
        return MetaInstagramClient(settings.meta_graph_api_base_url, settings.meta_graph_api_version, access_token)

    async def _maybe_long_lived(self, client: MetaInstagramOAuthClientProtocol, token: MetaTokenResult) -> MetaTokenResult:
        return await client.exchange_long_lived(access_token=token.access_token)

    async def _activate_webhook_subscription(self, connection: InstagramConnection, access_token: str) -> None:
        if not connection.instagram_account_id:
            self._mark_webhook_inactive(connection, "META_ACCOUNT_IDENTITY_MISSING", "Instagram account identity is missing.")
            return
        client = self._subscription_client(access_token)
        try:
            result = await client.subscribe_webhooks(connection.instagram_account_id, WEBHOOK_SUBSCRIPTIONS)
            if not result.success:
                self._mark_webhook_inactive(connection, "META_WEBHOOK_SUBSCRIPTION_FAILED", "Meta webhook subscription failed.")
                return
            verified = await client.get_webhook_subscription(connection.instagram_account_id)
        except MetaInstagramError as exc:
            self._mark_webhook_inactive(connection, exc.code, exc.message)
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

    def _is_operational(self, connection: InstagramConnection | None) -> bool:
        return bool(
            connection
            and connection.status == InstagramConnectionStatus.CONNECTED.value
            and connection.access_token_ciphertext
        )

    def _apply_profile(self, connection: InstagramConnection, profile) -> None:
        connection.instagram_account_id = profile.instagram_account_id
        connection.instagram_username = profile.username
        connection.instagram_account_type = profile.account_type
        connection.granted_permissions = profile.granted_permissions

    def _persist_callback_failure(
        self,
        existing: InstagramConnection | None,
        workspace_id: UUID,
        user_id: UUID,
        meta_app_id: str | None,
        code: str,
        message: str,
        *,
        profile=None,
    ) -> InstagramConnection:
        connection = existing or self.repo.create(InstagramConnection(workspace_id=workspace_id, created_by=user_id))
        if profile is not None:
            self._apply_profile(connection, profile)
        connection.meta_app_id = meta_app_id
        connection.status = InstagramConnectionStatus.FAILED.value
        connection.last_error_code = code
        connection.last_error_message = message[:300]
        connection.access_token_ciphertext = None
        connection.access_token_nonce = None
        connection.access_token_key_version = None
        connection.updated_by = user_id
        return connection

    def _copy_candidate(self, target: InstagramConnection, candidate: InstagramConnection) -> None:
        target.meta_app_id = candidate.meta_app_id
        target.instagram_account_id = candidate.instagram_account_id
        target.instagram_username = candidate.instagram_username
        target.instagram_account_type = candidate.instagram_account_type
        target.granted_permissions = list(candidate.granted_permissions or [])
        target.subscribed_webhook_fields = list(candidate.subscribed_webhook_fields or [])
        target.access_token_ciphertext = candidate.access_token_ciphertext
        target.access_token_nonce = candidate.access_token_nonce
        target.access_token_key_version = candidate.access_token_key_version
        target.token_expires_at = candidate.token_expires_at
        target.token_last_validated_at = candidate.token_last_validated_at
        target.connected_at = candidate.connected_at
        target.disconnected_at = candidate.disconnected_at
        target.status = candidate.status
        target.last_error_code = candidate.last_error_code
        target.last_error_message = candidate.last_error_message
        target.updated_by = candidate.updated_by
