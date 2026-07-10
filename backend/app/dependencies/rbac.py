from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status

from app.dependencies.auth import get_current_user
from app.models.role import RoleName
from app.models.user import User

ROLE_RANK = {
    RoleName.OWNER: 3,
    RoleName.MANAGER: 2,
    RoleName.ANALYST: 1,
}


def get_workspace_id(x_workspace_id: UUID | None = Header(default=None, alias="X-Workspace-ID")) -> UUID:
    if x_workspace_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Workspace-ID header is required")
    return x_workspace_id


def get_user_role_for_workspace(user: User, workspace_id: UUID) -> RoleName | None:
    for membership in user.workspaces:
        if membership.workspace_id == workspace_id and membership.workspace.is_active and getattr(membership, "is_active", True):
            return RoleName(membership.role.name)
    return None


def require_roles(*allowed_roles: RoleName) -> Callable[[User, UUID], User]:
    def guard(user: User = Depends(get_current_user), workspace_id: UUID = Depends(get_workspace_id)) -> User:
        role = get_user_role_for_workspace(user, workspace_id)
        if role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient workspace permissions")
        return user
    return guard


def require_min_role(minimum_role: RoleName) -> Callable[[User, UUID], User]:
    def guard(user: User = Depends(get_current_user), workspace_id: UUID = Depends(get_workspace_id)) -> User:
        role = get_user_role_for_workspace(user, workspace_id)
        if role is None or ROLE_RANK[role] < ROLE_RANK[minimum_role]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient workspace permissions")
        return user
    return guard
