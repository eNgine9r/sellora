from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.rbac import get_workspace_id
from app.models.role import RoleName
from app.models.user import User
from app.models.workspace_user import WorkspaceUser
from app.schemas.workspace import WorkspaceUserCreate, WorkspaceUserResponse, WorkspaceUserRoleUpdate
from app.services.workspace_service import WorkspacePermissionError, WorkspaceService, WorkspaceValidationError

router = APIRouter(prefix="/workspace-users", tags=["Workspace users"])


def _full_name(user: User) -> str:
    return " ".join(part for part in [user.first_name, user.last_name] if part).strip()


def _response(membership: WorkspaceUser) -> WorkspaceUserResponse:
    return WorkspaceUserResponse(user_id=membership.user_id, email=membership.user.email, full_name=_full_name(membership.user), role=RoleName(membership.role.name), is_active=membership.is_active)


def _handle_error(exc: Exception) -> None:
    if isinstance(exc, WorkspacePermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient workspace permissions") from exc
    if isinstance(exc, WorkspaceValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[WorkspaceUserResponse])
def list_workspace_users(workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[WorkspaceUserResponse]:
    try:
        return [_response(membership) for membership in WorkspaceService(db).list_workspace_users(workspace_id, current_user.id)]
    except (WorkspacePermissionError, WorkspaceValidationError) as exc:
        _handle_error(exc)
        raise


@router.post("", response_model=WorkspaceUserResponse, status_code=status.HTTP_201_CREATED)
def add_workspace_user(payload: WorkspaceUserCreate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> WorkspaceUserResponse:
    try:
        return _response(WorkspaceService(db).add_workspace_user(workspace_id, payload, current_user.id))
    except (WorkspacePermissionError, WorkspaceValidationError) as exc:
        _handle_error(exc)
        raise


@router.put("/{user_id}/role", response_model=WorkspaceUserResponse)
def change_workspace_user_role(user_id: UUID, payload: WorkspaceUserRoleUpdate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> WorkspaceUserResponse:
    try:
        return _response(WorkspaceService(db).change_user_role(workspace_id, user_id, payload.role, current_user.id))
    except (WorkspacePermissionError, WorkspaceValidationError) as exc:
        _handle_error(exc)
        raise


@router.patch("/{user_id}/deactivate", response_model=WorkspaceUserResponse)
def deactivate_workspace_user(user_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> WorkspaceUserResponse:
    try:
        return _response(WorkspaceService(db).deactivate_user(workspace_id, user_id, current_user.id))
    except (WorkspacePermissionError, WorkspaceValidationError) as exc:
        _handle_error(exc)
        raise
