from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.feedback import PilotFeedbackCreate, PilotFeedbackResponse, PilotFeedbackUpdate
from app.services.feedback_service import PilotFeedbackService

router = APIRouter(prefix="/feedback", tags=["Pilot Feedback"])


@router.post("", response_model=PilotFeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: PilotFeedbackCreate,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.ANALYST)),
    user_agent: str | None = Header(default=None, alias="User-Agent"),
    db: Session = Depends(get_db),
) -> PilotFeedbackResponse:
    return PilotFeedbackService(db).submit(workspace_id, payload, current_user.id, user_agent)


@router.get("", response_model=list[PilotFeedbackResponse])
def list_feedback(
    workspace_id: UUID = Depends(get_workspace_id),
    _current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> list[PilotFeedbackResponse]:
    return PilotFeedbackService(db).list(workspace_id)


@router.patch("/{feedback_id}", response_model=PilotFeedbackResponse)
def update_feedback_status(
    feedback_id: UUID,
    payload: PilotFeedbackUpdate,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.OWNER)),
    db: Session = Depends(get_db),
) -> PilotFeedbackResponse:
    record = PilotFeedbackService(db).update_status(workspace_id, feedback_id, payload, current_user.id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    return record
