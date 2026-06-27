from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.workspace import WorkspaceSettingsResponse, WorkspaceSettingsUpdate
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.get("/current", response_model=WorkspaceSettingsResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def get_current_workspace_settings(workspace_id: UUID = Depends(get_workspace_id), db: Session = Depends(get_db)) -> WorkspaceSettingsResponse:
    workspace = WorkspaceService(db).get_settings(workspace_id)
    if workspace is None or not workspace.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return WorkspaceSettingsResponse(id=workspace.id, name=workspace.name, slug=workspace.slug, currency_code=workspace.currency_code)


@router.put("/current", response_model=WorkspaceSettingsResponse)
def update_current_workspace_settings(payload: WorkspaceSettingsUpdate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.OWNER)), db: Session = Depends(get_db)) -> WorkspaceSettingsResponse:
    workspace = WorkspaceService(db).update_settings(workspace_id, payload, current_user.id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return WorkspaceSettingsResponse(id=workspace.id, name=workspace.name, slug=workspace.slug, currency_code=workspace.currency_code)
