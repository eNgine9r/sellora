from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.dependencies.rbac import get_user_role_for_workspace, require_min_role, require_roles
from app.dependencies.tenant import require_workspace_access
from app.models.role import RoleName


def _membership(workspace_id, role: RoleName, *, membership_active: bool = True, workspace_active: bool = True):
    return SimpleNamespace(
        workspace_id=workspace_id,
        is_active=membership_active,
        role=SimpleNamespace(name=role.value),
        workspace=SimpleNamespace(is_active=workspace_active),
    )


def _user(workspaces):
    return SimpleNamespace(id=uuid4(), workspaces=workspaces)


def test_role_resolution_requires_active_membership_and_active_workspace() -> None:
    workspace_id = uuid4()

    assert get_user_role_for_workspace(_user([_membership(workspace_id, RoleName.OWNER)]), workspace_id) == RoleName.OWNER
    assert get_user_role_for_workspace(_user([_membership(workspace_id, RoleName.OWNER, membership_active=False)]), workspace_id) is None
    assert get_user_role_for_workspace(_user([_membership(workspace_id, RoleName.OWNER, workspace_active=False)]), workspace_id) is None
    assert get_user_role_for_workspace(_user([_membership(uuid4(), RoleName.OWNER)]), workspace_id) is None


def test_workspace_access_denies_valid_user_without_membership() -> None:
    workspace_id = uuid4()

    with pytest.raises(HTTPException) as exc:
        require_workspace_access(workspace_id=workspace_id, user=_user([]))

    assert exc.value.status_code == 403
    assert exc.value.detail == "Workspace access denied"


@pytest.mark.parametrize("role", [RoleName.MANAGER, RoleName.ANALYST])
def test_owner_only_guard_denies_non_owner_roles(role: RoleName) -> None:
    workspace_id = uuid4()
    guard = require_roles(RoleName.OWNER)

    with pytest.raises(HTTPException) as exc:
        guard(user=_user([_membership(workspace_id, role)]), workspace_id=workspace_id)

    assert exc.value.status_code == 403


def test_min_role_guard_allows_manager_operations_but_denies_analyst_mutation() -> None:
    workspace_id = uuid4()
    manager_guard = require_min_role(RoleName.MANAGER)

    assert manager_guard(user=_user([_membership(workspace_id, RoleName.MANAGER)]), workspace_id=workspace_id).workspaces
    with pytest.raises(HTTPException) as exc:
        manager_guard(user=_user([_membership(workspace_id, RoleName.ANALYST)]), workspace_id=workspace_id)

    assert exc.value.status_code == 403
