from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workspace_subscription import WorkspaceSubscription


class SubscriptionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_workspace(self, workspace_id: UUID) -> WorkspaceSubscription | None:
        statement = select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace_id)
        return self.db.execute(statement).scalar_one_or_none()
