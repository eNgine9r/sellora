from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.v1.workspace_memos import router
from app.database.base import Base
from app.models.workspace_memo import WorkspaceMemo
from app.repositories.workspace_memo_repository import WorkspaceMemoRepository
from app.schemas.workspace_memo import WorkspaceMemoCreate, WorkspaceMemoUpdate
from app.services.workspace_memo_service import WorkspaceMemoService


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[WorkspaceMemo.__table__])
    with Session(engine) as session:
        yield session
    engine.dispose()


def service_for(db):
    service = WorkspaceMemoService(db)
    class FakeAudit:
        records = []
        def create(self, **kwargs):
            self.records.append(kwargs)
    service.audit = FakeAudit()
    return service


def test_workspace_notes_are_persisted_and_isolated(db):
    first, second, actor = uuid4(), uuid4(), uuid4()
    service = service_for(db)
    created = service.create(first, WorkspaceMemoCreate(kind="NOTE", title="  Call courier  ", body="Check pickup"), actor)
    assert created.title == "Call courier"
    assert created.created_by == actor
    assert len(service.list(first)) == 1
    assert service.list(second) == []
    assert service.update(second, created.id, WorkspaceMemoUpdate(title="Hijacked"), actor) is None
    assert service.delete(second, created.id, actor) is False
    assert service.memos.get(second, created.id) is None
    assert service.memos.get(first, created.id).title == "Call courier"
    assert "Check pickup" not in str(service.audit.records)


def test_task_edit_completion_and_soft_delete(db):
    workspace, actor = uuid4(), uuid4()
    service = service_for(db)
    task = service.create(workspace, WorkspaceMemoCreate(kind="TASK", title="Send parcel", due_on=date(2026, 10, 28)), actor)
    task = service.update(workspace, task.id, WorkspaceMemoUpdate(is_done=True, is_pinned=True), actor)
    assert task is not None and task.is_done and task.is_pinned
    assert task.due_on == date(2026, 10, 28)
    assert service.delete(workspace, task.id, actor) is True
    assert service.list(workspace) == []
    assert db.get(WorkspaceMemo, task.id).deleted_at is not None


def test_note_due_date_rejected():
    with pytest.raises(ValidationError):
        WorkspaceMemoCreate(kind="NOTE", title="Not a task", due_on=date.today())
    with pytest.raises(ValidationError):
        WorkspaceMemoCreate(kind="NOTE", title="   ")
    with pytest.raises(ValidationError):
        WorkspaceMemoUpdate(title="  ")


def test_non_nullable_fields_cannot_be_patched_to_null(db):
    service = service_for(db)
    workspace = uuid4()
    actor = uuid4()
    note = service.create(workspace, WorkspaceMemoCreate(title="Keep me"), actor)
    with pytest.raises(ValueError):
        service.update(workspace, note.id, WorkspaceMemoUpdate(body=None), actor)
    assert service.memos.get(workspace, note.id).title == "Keep me"


def test_workspace_memos_route_has_role_guard_and_four_methods():
    methods = {(method, route.path) for route in router.routes for method in route.methods}
    assert methods == {
        ("GET", "/workspace-memos"),
        ("POST", "/workspace-memos"),
        ("PATCH", "/workspace-memos/{memo_id}"),
        ("DELETE", "/workspace-memos/{memo_id}"),
    }
    for route in router.routes:
        assert any(dep.call.__name__ == "guard" for dep in route.dependant.dependencies)
