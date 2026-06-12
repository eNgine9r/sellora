from uuid import UUID

from sqlalchemy.orm import Session

from app.models.pilot_feedback import PilotFeedback, PilotFeedbackStatus
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.feedback_repository import PilotFeedbackRepository
from app.schemas.feedback import PilotFeedbackCreate, PilotFeedbackUpdate
from app.services.business_utils import snapshot


class PilotFeedbackService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.feedback = PilotFeedbackRepository(db)
        self.audit_logs = AuditLogRepository(db)

    def submit(self, workspace_id: UUID, payload: PilotFeedbackCreate, user_id: UUID | None, user_agent: str | None = None) -> PilotFeedback:
        record = PilotFeedback(
            workspace_id=workspace_id,
            user_id=user_id,
            category=payload.category.value,
            rating=payload.rating,
            message=payload.message.strip(),
            page_path=payload.page_path,
            user_agent=(user_agent or None),
            status=PilotFeedbackStatus.NEW.value,
        )
        self.feedback.create(record)
        self.db.flush()
        self.audit_logs.create(workspace_id=workspace_id, user_id=user_id, entity_type="PilotFeedback", entity_id=record.id, action="PILOT_FEEDBACK_SUBMIT", new_value={"category": record.category, "rating": record.rating, "page_path": record.page_path})
        self.db.commit()
        self.db.refresh(record)
        return record

    def list(self, workspace_id: UUID) -> list[PilotFeedback]:
        return self.feedback.list_for_workspace(workspace_id)

    def update_status(self, workspace_id: UUID, feedback_id: UUID, payload: PilotFeedbackUpdate, actor_user_id: UUID | None) -> PilotFeedback | None:
        record = self.feedback.get_for_workspace(workspace_id, feedback_id)
        if record is None:
            return None
        old_value = snapshot(record)
        record.status = payload.status.value
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="PilotFeedback", entity_id=record.id, action="PILOT_FEEDBACK_STATUS_UPDATE", old_value=old_value, new_value=snapshot(record))
        self.db.commit()
        self.db.refresh(record)
        return record
