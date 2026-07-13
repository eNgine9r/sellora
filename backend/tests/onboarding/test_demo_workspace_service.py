from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.role import RoleName
from app.services.workspace_service import WorkspaceService, WorkspaceValidationError, is_demo_workspace_slug


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


class FakeWorkspaces:
    def __init__(self, existing=None, slug_exists=False):
        self.existing = existing
        self.slug_exists = slug_exists
        self.created = []
        self.memberships = []

    def find_active_demo_for_user(self, user_id):
        return self.existing

    def get_by_slug(self, slug):
        return SimpleNamespace(slug=slug) if self.slug_exists else None

    def create_workspace(self, *, name, slug, currency_code, timezone):
        workspace = SimpleNamespace(id=uuid4(), name=name, slug=slug, currency_code=currency_code, timezone=timezone, is_active=True)
        self.created.append(workspace)
        return workspace

    def add_membership(self, *, workspace_id, user_id, role):
        membership = SimpleNamespace(workspace_id=workspace_id, user_id=user_id, role=SimpleNamespace(name=role.value), workspace=self.created[-1], is_active=True)
        self.memberships.append(membership)
        return membership

    def get_active_membership(self, workspace_id, user_id):
        for membership in self.memberships:
            if membership.workspace_id == workspace_id and membership.user_id == user_id and membership.is_active:
                return membership
        return None

    def count_active_owners(self, workspace_id):
        return 1


def _service(workspaces):
    service = WorkspaceService.__new__(WorkspaceService)
    service.db = FakeDb()
    service.workspaces = workspaces
    service.audit_logs = FakeAudit()
    service._seed_demo_dataset = lambda workspace_id, actor_user_id: service.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Workspace", entity_id=workspace_id, action="DEMO_WORKSPACE_CREATE")
    return service


def test_demo_workspace_creation_is_idempotent_when_active_demo_exists() -> None:
    existing = SimpleNamespace(workspace_id=uuid4(), workspace=SimpleNamespace(slug="demo-sellora-existing"), role=SimpleNamespace(name=RoleName.OWNER.value))
    service = _service(FakeWorkspaces(existing=existing))

    result = service.create_or_get_demo_workspace(uuid4())

    assert result is existing
    assert service.workspaces.created == []
    assert service.db.commits == 0


def test_demo_workspace_creation_assigns_owner_and_does_not_accept_target_workspace() -> None:
    user_id = uuid4()
    service = _service(FakeWorkspaces())

    membership = service.create_or_get_demo_workspace(user_id, locale="uk", currency_code="UAH")

    assert membership.user_id == user_id
    assert membership.role.name == RoleName.OWNER.value
    assert membership.workspace.slug.startswith("demo-sellora-")
    assert service.db.commits == 1
    assert service.audit_logs.records[0]["action"] == "DEMO_WORKSPACE_CREATE"


def test_demo_workspace_generation_rolls_back_on_failure() -> None:
    service = _service(FakeWorkspaces())
    service._seed_demo_dataset = lambda *_args: (_ for _ in ()).throw(RuntimeError("synthetic failure"))

    with pytest.raises(RuntimeError):
        service.create_or_get_demo_workspace(uuid4())

    assert service.db.rollbacks == 1
    assert service.db.commits == 0


def test_demo_deactivation_only_allows_demo_slug() -> None:
    user_id = uuid4()
    service = _service(FakeWorkspaces())
    membership = service.create_or_get_demo_workspace(user_id)
    membership.workspace.slug = "real-shop"

    with pytest.raises(WorkspaceValidationError):
        service.deactivate_demo_workspace(membership.workspace_id, user_id)


def test_demo_slug_detection_is_explicit() -> None:
    assert is_demo_workspace_slug("demo-sellora-abc") is True
    assert is_demo_workspace_slug("sellora-demo") is True
    assert is_demo_workspace_slug("real-demo-looking-shop") is False
