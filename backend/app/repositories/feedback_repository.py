from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pilot_feedback import PilotFeedback


class PilotFeedbackRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, feedback: PilotFeedback) -> PilotFeedback:
        self.db.add(feedback)
        return feedback

    def list_for_workspace(self, workspace_id: UUID, limit: int = 100) -> list[PilotFeedback]:
        return list(
            self.db.execute(
                select(PilotFeedback)
                .where(PilotFeedback.workspace_id == workspace_id, PilotFeedback.deleted_at.is_(None))
                .order_by(PilotFeedback.created_at.desc())
                .limit(limit)
            ).scalars()
        )

    def get_for_workspace(self, workspace_id: UUID, feedback_id: UUID) -> PilotFeedback | None:
        return self.db.execute(
            select(PilotFeedback).where(PilotFeedback.id == feedback_id, PilotFeedback.workspace_id == workspace_id, PilotFeedback.deleted_at.is_(None))
        ).scalar_one_or_none()
