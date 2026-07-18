from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import UUID
import hashlib, secrets
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.integrations.meta_instagram.config import REQUIRED_MESSAGING_PERMISSION
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.repositories.connection_repository import MetaOAuthStateRepository
from app.models.meta_instagram import MetaOAuthState

class InstagramOAuthService:
    def __init__(self, db: Session) -> None: self.db = db
    def start(self, workspace_id: UUID, user_id: UUID):
        settings = get_settings()
        if not settings.meta_app_id or not settings.meta_oauth_redirect_uri:
            raise MetaInstagramError("META_CONFIGURATION_MISSING", "Instagram OAuth is not configured.", 409)
        raw_state = secrets.token_urlsafe(32)
        state_hash = hashlib.sha256(raw_state.encode()).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        MetaOAuthStateRepository(self.db).create(MetaOAuthState(workspace_id=workspace_id, user_id=user_id, state_hash=state_hash, redirect_uri=settings.meta_oauth_redirect_uri, expires_at=expires_at, created_at=datetime.now(UTC)))
        params = urlencode({"client_id": settings.meta_app_id, "redirect_uri": settings.meta_oauth_redirect_uri, "scope": REQUIRED_MESSAGING_PERMISSION, "response_type": "code", "state": raw_state})
        return f"{settings.meta_instagram_oauth_authorize_url}?{params}", expires_at
    def validate_state(self, state: str, workspace_id: UUID | None = None, user_id: UUID | None = None) -> MetaOAuthState:
        row = MetaOAuthStateRepository(self.db).get_by_hash_for_update(hashlib.sha256(state.encode()).hexdigest())
        if not row: raise MetaInstagramError("META_OAUTH_STATE_INVALID", "OAuth state is invalid.", 400)
        if row.expires_at < datetime.now(UTC): raise MetaInstagramError("META_OAUTH_STATE_EXPIRED", "OAuth state has expired.", 400)
        if row.consumed_at: raise MetaInstagramError("META_OAUTH_STATE_ALREADY_USED", "OAuth state was already used.", 409)
        if workspace_id is not None and row.workspace_id != workspace_id: raise MetaInstagramError("META_OAUTH_STATE_INVALID", "OAuth state workspace mismatch.", 403)
        if user_id is not None and row.user_id != user_id: raise MetaInstagramError("META_OAUTH_STATE_INVALID", "OAuth state user mismatch.", 403)
        return row
