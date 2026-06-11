from types import SimpleNamespace
from uuid import uuid4

from app.dependencies.rbac import ROLE_RANK, get_user_role_for_workspace
from app.models.role import RoleName


def _membership(workspace_id, role: RoleName, is_active: bool = True):
    return SimpleNamespace(
        workspace_id=workspace_id,
        role=SimpleNamespace(name=role.value),
        workspace=SimpleNamespace(is_active=is_active),
    )


def test_user_role_is_resolved_only_for_active_workspace_membership() -> None:
    workspace_id = uuid4()
    user = SimpleNamespace(workspaces=[_membership(workspace_id, RoleName.MANAGER)])

    assert get_user_role_for_workspace(user, workspace_id) == RoleName.MANAGER
    assert get_user_role_for_workspace(user, uuid4()) is None


def test_inactive_workspace_membership_does_not_authorize_user() -> None:
    workspace_id = uuid4()
    user = SimpleNamespace(workspaces=[_membership(workspace_id, RoleName.OWNER, is_active=False)])

    assert get_user_role_for_workspace(user, workspace_id) is None


def test_role_hierarchy_owner_manager_analyst() -> None:
    assert ROLE_RANK[RoleName.OWNER] > ROLE_RANK[RoleName.MANAGER] > ROLE_RANK[RoleName.ANALYST]
