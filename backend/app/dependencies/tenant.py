from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.dependencies.rbac import get_user_role_for_workspace, get_workspace_id
from app.models.user import User


def require_workspace_access(workspace_id: UUID = Depends(get_workspace_id), user: User = Depends(get_current_user)) -> UUID:
    if get_user_role_for_workspace(user, workspace_id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace access denied")
    return workspace_id
