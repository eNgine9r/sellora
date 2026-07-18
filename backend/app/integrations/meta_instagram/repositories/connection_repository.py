from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.meta_instagram import InstagramConnection, InstagramConnectionStatus, MetaOAuthState

class InstagramConnectionRepository:
    def __init__(self, db: Session) -> None: self.db = db
    def get_active(self, workspace_id: UUID) -> InstagramConnection | None:
        return self.db.execute(select(InstagramConnection).where(InstagramConnection.workspace_id == workspace_id, InstagramConnection.deleted_at.is_(None)).order_by(InstagramConnection.created_at.desc())).scalar_one_or_none()
    def get(self, workspace_id: UUID, connection_id: UUID) -> InstagramConnection | None:
        return self.db.execute(select(InstagramConnection).where(InstagramConnection.workspace_id == workspace_id, InstagramConnection.id == connection_id, InstagramConnection.deleted_at.is_(None))).scalar_one_or_none()
    def get_by_account(self, instagram_account_id: str) -> InstagramConnection | None:
        return self.db.execute(select(InstagramConnection).where(InstagramConnection.instagram_account_id == instagram_account_id, InstagramConnection.status == InstagramConnectionStatus.CONNECTED.value, InstagramConnection.deleted_at.is_(None))).scalar_one_or_none()
    def create(self, connection: InstagramConnection) -> InstagramConnection:
        self.db.add(connection); self.db.flush(); return connection

class MetaOAuthStateRepository:
    def __init__(self, db: Session) -> None: self.db = db
    def create(self, state: MetaOAuthState) -> MetaOAuthState:
        self.db.add(state); self.db.flush(); return state
    def get_by_hash_for_update(self, state_hash: str) -> MetaOAuthState | None:
        return self.db.execute(select(MetaOAuthState).where(MetaOAuthState.state_hash == state_hash).with_for_update()).scalar_one_or_none()
