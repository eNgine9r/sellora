from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.rbac import get_workspace_id
from app.models.role import RoleName
from app.models.user import User
from app.models.workspace_user import WorkspaceUser
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse, WorkspaceSettingsResponse, WorkspaceSettingsUpdate
from app.services.workspace_service import WorkspacePermissionError, WorkspaceService, WorkspaceValidationError

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


def _membership_response(membership: WorkspaceUser) -> WorkspaceResponse:
    workspace = membership.workspace
    return WorkspaceResponse(id=workspace.id, name=workspace.name, slug=workspace.slug, currency_code=workspace.currency_code, timezone=getattr(workspace, "timezone", "Europe/Kyiv"), role=RoleName(membership.role.name), is_active=workspace.is_active)


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[WorkspaceResponse]:
    return [_membership_response(membership) for membership in WorkspaceService(db).list_available_workspaces(current_user.id)]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(payload: WorkspaceCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> WorkspaceResponse:
    try:
        return _membership_response(WorkspaceService(db).create_workspace(payload, current_user.id))
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/current", response_model=WorkspaceSettingsResponse)
def get_current_workspace_settings(workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> WorkspaceSettingsResponse:
    membership = WorkspaceService(db).get_current_workspace(workspace_id, current_user.id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace access denied")
    workspace = membership.workspace
    return WorkspaceSettingsResponse(id=workspace.id, name=workspace.name, slug=workspace.slug, currency_code=workspace.currency_code, timezone=getattr(workspace, "timezone", "Europe/Kyiv"), role=RoleName(membership.role.name), is_active=workspace.is_active)


@router.put("/current", response_model=WorkspaceSettingsResponse)
def update_current_workspace_settings(payload: WorkspaceSettingsUpdate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> WorkspaceSettingsResponse:
    service = WorkspaceService(db)
    try:
        workspace = service.update_settings(workspace_id, payload, current_user.id)
    except WorkspacePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient workspace permissions") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    membership = service.get_current_workspace(workspace_id, current_user.id)
    return WorkspaceSettingsResponse(id=workspace.id, name=workspace.name, slug=workspace.slug, currency_code=workspace.currency_code, timezone=getattr(workspace, "timezone", "Europe/Kyiv"), role=RoleName(membership.role.name) if membership else None, is_active=workspace.is_active)
