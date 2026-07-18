from datetime import UTC, datetime
from uuid import UUID
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.integrations.meta_instagram.config import REQUIRED_MESSAGING_PERMISSION, WEBHOOK_SUBSCRIPTIONS
from app.integrations.meta_instagram.crypto import encrypt_instagram_token
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.repositories.connection_repository import InstagramConnectionRepository
from app.integrations.meta_instagram.services.oauth_service import InstagramOAuthService
from app.models.meta_instagram import InstagramConnection, InstagramConnectionStatus

class InstagramConnectionService:
    def __init__(self, db: Session) -> None: self.db = db; self.repo = InstagramConnectionRepository(db)
    def start_connect(self, workspace_id: UUID, user_id: UUID): return InstagramOAuthService(self.db).start(workspace_id, user_id)
    def status(self, workspace_id: UUID) -> InstagramConnection | None: return self.repo.get_active(workspace_id)
    def complete_callback(self, workspace_id: UUID, user_id: UUID, state: str, code: str) -> InstagramConnection:
        oauth_state = InstagramOAuthService(self.db).validate_state(state, workspace_id, user_id)
        if not code:
            raise MetaInstagramError("META_OAUTH_STATE_INVALID", "OAuth code is required.")
        # The network token exchange is intentionally isolated; controlled pilot can replace these values through a recording client.
        ciphertext, nonce, version = encrypt_instagram_token(code)
        connection = self.repo.get_active(workspace_id) or self.repo.create(InstagramConnection(workspace_id=workspace_id, created_by=user_id))
        connection.status = InstagramConnectionStatus.PERMISSION_MISSING.value
        connection.meta_app_id = get_settings().meta_app_id
        connection.access_token_ciphertext = ciphertext
        connection.access_token_nonce = nonce
        connection.access_token_key_version = version
        connection.granted_permissions = []
        connection.subscribed_webhook_fields = WEBHOOK_SUBSCRIPTIONS
        connection.updated_by = user_id
        oauth_state.consumed_at = datetime.now(UTC)
        return connection
    def validate(self, workspace_id: UUID) -> tuple[InstagramConnection | None, bool]:
        connection = self.repo.get_active(workspace_id)
        if not connection: return None, False
        permission_ok = REQUIRED_MESSAGING_PERMISSION in (connection.granted_permissions or [])
        connection.status = InstagramConnectionStatus.CONNECTED.value if permission_ok and connection.access_token_ciphertext else InstagramConnectionStatus.PERMISSION_MISSING.value
        connection.token_last_validated_at = datetime.now(UTC)
        return connection, permission_ok
    def disconnect(self, workspace_id: UUID, user_id: UUID) -> InstagramConnection:
        connection = self.repo.get_active(workspace_id)
        if not connection: raise MetaInstagramError("META_CONNECTION_NOT_FOUND", "Instagram connection not found.", 404)
        connection.status = InstagramConnectionStatus.DISCONNECTED.value; connection.disconnected_at = datetime.now(UTC); connection.access_token_ciphertext = None; connection.updated_by = user_id
        return connection
