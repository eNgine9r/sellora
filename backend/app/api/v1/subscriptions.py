from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_roles
from app.models.role import RoleName
from app.models.user import User
from app.schemas.subscription import SubscriptionStatusResponse
from app.services.subscription_service import SubscriptionAccessError, SubscriptionService

router = APIRouter(prefix="/workspaces/current/subscription", tags=["Subscriptions"])


@router.get("", response_model=SubscriptionStatusResponse)
def get_workspace_subscription(
    response: Response,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_roles(RoleName.OWNER)),
    db: Session = Depends(get_db),
) -> SubscriptionStatusResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        return SubscriptionService(db).get_status(workspace_id, current_user.id)
    except SubscriptionAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace access denied") from exc
