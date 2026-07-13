from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.rbac import get_workspace_id
from app.models.user import User
from app.schemas.onboarding import OnboardingStatusResponse
from app.services.onboarding_service import OnboardingAccessError, OnboardingService

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


@router.get("/status", response_model=OnboardingStatusResponse)
def get_onboarding_status(workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> OnboardingStatusResponse:
    try:
        return OnboardingService(db).get_status(workspace_id, current_user.id)
    except OnboardingAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace access denied") from exc
