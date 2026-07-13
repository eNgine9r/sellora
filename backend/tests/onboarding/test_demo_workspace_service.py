from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.role import RoleName
from app.repositories.audit_log_repository import DEMO_WORKSPACE_CREATE_ACTION
from app.services.workspace_service import WorkspacePermissionError, WorkspaceService, WorkspaceValidationError


class FakeDb:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.refreshed = []

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def refresh(self, item):
        self.refreshed.append(item)


class FakeAudit:
    def __init__(self):
        self.records = []

    def create(self, **kwargs):
        self.records.append(kwargs)

    def has_demo_workspace_provenance(self, workspace_id, *, creator_user_id=None):
        return any(
            record.get("workspace_id") == workspace_id
            and record.get("entity_type") == "Workspace"
            and str(record.get("entity_id")) == str(workspace_id)
            and record.get("action") == DEMO_WORKSPACE_CREATE_ACTION
            and (creator_user_id is None or record.get("user_id") == creator_user_id)
            for record in self.records
        )


class FakeWorkspaces:
    def __init__(self, memberships=None, slug_exists=False):
        self.slug_exists = slug_exists
        self.created = []
        self.memberships = list(memberships or [])

    def list_for_user(self, user_id):
        return [
            membership
            for membership in self.memberships
            if membership.user_id == user_id and membership.is_active and membership.workspace.is_active
        ]

    def get_by_slug(self, slug):
        return SimpleNamespace(slug=slug) if self.slug_exists else None

    def create_workspace(self, *, name, slug, currency_code, timezone):
        workspace = SimpleNamespace(id=uuid4(), name=name, slug=slug, currency_code=currency_code, timezone=timezone, is_active=True)
        self.created.append(workspace)
        return workspace

    def add_membership(self, *, workspace_id, user_id, role):
        workspace = next(workspace for workspace in self.created if workspace.id == workspace_id)
        membership = SimpleNamespace(workspace_id=workspace_id, user_id=user_id, role=SimpleNamespace(name=role.value), workspace=workspace, is_active=True)
        self.memberships.append(membership)
        return membership

    def get_active_membership(self, workspace_id, user_id):
        for membership in self.memberships:
            if (
                membership.workspace_id == workspace_id
                and membership.user_id == user_id
                and membership.is_active
                and membership.workspace.is_active
            ):
                return membership
        return None

    def count_active_owners(self, workspace_id):
        return 1


def membership(user_id, role=RoleName.OWNER, *, slug="real-shop"):
    workspace = SimpleNamespace(id=uuid4(), name="Workspace", slug=slug, is_active=True)
    return SimpleNamespace(
        workspace_id=workspace.id,
        user_id=user_id,
        role=SimpleNamespace(name=role.value),
        workspace=workspace,
        is_active=True,
    )


def _service(workspaces):
    service = WorkspaceService.__new__(WorkspaceService)
    service.db = FakeDb()
    service.workspaces = workspaces
    service.audit_logs = FakeAudit()
    service._seed_demo_dataset = lambda workspace_id, actor_user_id: service.audit_logs.create(
        workspace_id=workspace_id,
        user_id=actor_user_id,
        entity_type="Workspace",
        entity_id=workspace_id,
        action=DEMO_WORKSPACE_CREATE_ACTION,
    )
    return service


def test_demo_workspace_creation_is_idempotent_by_server_provenance() -> None:
    user_id = uuid4()
    service = _service(FakeWorkspaces())

    first = service.create_or_get_demo_workspace(user_id)
    second = service.create_or_get_demo_workspace(user_id)

    assert second is first
    assert len(service.workspaces.created) == 1
    assert service.db.commits == 1
    assert service.audit_logs.has_demo_workspace_provenance(first.workspace_id, creator_user_id=user_id)


def test_demo_workspace_creation_assigns_owner_and_does_not_accept_target_workspace() -> None:
    user_id = uuid4()
    service = _service(FakeWorkspaces())

    created = service.create_or_get_demo_workspace(user_id, locale="uk", currency_code="UAH")

    assert created.user_id == user_id
    assert created.role.name == RoleName.OWNER.value
    assert created.workspace.slug.startswith("demo-sellora-")
    assert service.db.commits == 1
    assert service.audit_logs.records[0]["action"] == DEMO_WORKSPACE_CREATE_ACTION


@pytest.mark.parametrize("role", [RoleName.MANAGER, RoleName.ANALYST])
def test_non_owner_membership_cannot_create_demo_workspace(role: RoleName) -> None:
    user_id = uuid4()
    service = _service(FakeWorkspaces([membership(user_id, role)]))

    with pytest.raises(WorkspacePermissionError):
        service.create_or_get_demo_workspace(user_id)

    assert service.workspaces.created == []
    assert service.db.commits == 0


def test_user_without_workspace_can_create_demo_workspace() -> None:
    user_id = uuid4()
    service = _service(FakeWorkspaces())

    created = service.create_or_get_demo_workspace(user_id)

    assert created.role.name == RoleName.OWNER.value


def test_demo_workspace_generation_rolls_back_on_failure() -> None:
    service = _service(FakeWorkspaces())
    service._seed_demo_dataset = lambda *_args: (_ for _ in ()).throw(RuntimeError("synthetic failure"))

    with pytest.raises(RuntimeError):
        service.create_or_get_demo_workspace(uuid4())

    assert service.db.rollbacks == 1
    assert service.db.commits == 0


def test_demo_looking_slug_without_provenance_is_rejected() -> None:
    user_id = uuid4()
    forged = membership(user_id, slug="demo-sellora-forged")
    service = _service(FakeWorkspaces([forged]))

    with pytest.raises(WorkspaceValidationError):
        service.deactivate_demo_workspace(forged.workspace_id, user_id)

    assert forged.workspace.is_active is True
    assert forged.is_active is True


def test_provenance_allows_deactivation_even_when_slug_does_not_look_demo() -> None:
    user_id = uuid4()
    provenanced = membership(user_id, slug="renamed-workspace")
    service = _service(FakeWorkspaces([provenanced]))
    service.audit_logs.create(
        workspace_id=provenanced.workspace_id,
        user_id=user_id,
        entity_type="Workspace",
        entity_id=provenanced.workspace_id,
        action=DEMO_WORKSPACE_CREATE_ACTION,
    )

    result = service.deactivate_demo_workspace(provenanced.workspace_id, user_id)

    assert result.workspace.is_active is False
    assert result.is_active is False
    assert service.audit_logs.records[-1]["action"] == "DEMO_WORKSPACE_DEACTIVATE"
