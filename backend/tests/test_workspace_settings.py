from types import SimpleNamespace
from uuid import uuid4

from pydantic import ValidationError

from app.models.workspace import Workspace
from app.schemas.workspace import CurrencyCode, WorkspaceSettingsUpdate
from app.services.workspace_service import WorkspaceService


class FakeDb:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def get(self, model, model_id):
        if model is Workspace and model_id == self.workspace.id:
            return self.workspace
        return None

    def commit(self) -> None:
        pass

    def refresh(self, model) -> None:
        pass


class FakeAuditLogs:
    def __init__(self) -> None:
        self.records = []

    def create(self, **kwargs):
        self.records.append(kwargs)
        return SimpleNamespace(**kwargs)


def _service() -> tuple[WorkspaceService, Workspace]:
    workspace = Workspace(id=uuid4(), name="Workspace", slug="workspace", currency_code="UAH", is_active=True)
    service = WorkspaceService.__new__(WorkspaceService)
    service.db = FakeDb(workspace)
    service.audit_logs = FakeAuditLogs()
    return service, workspace


def test_workspace_currency_defaults_to_uah() -> None:
    assert Workspace.__table__.c.currency_code.default.arg == "UAH"
    assert Workspace.__table__.c.currency_code.server_default.arg == "UAH"


def test_workspace_currency_can_update_to_usd() -> None:
    service, workspace = _service()
    actor_id = uuid4()

    updated = service.update_settings(workspace.id, WorkspaceSettingsUpdate(currency_code=CurrencyCode.USD), actor_id)

    assert updated.currency_code == "USD"
    assert service.audit_logs.records[-1]["action"] == "WORKSPACE_CURRENCY_UPDATE"


def test_invalid_workspace_currency_is_rejected() -> None:
    try:
        WorkspaceSettingsUpdate.model_validate({"currency_code": "EUR"})
    except ValidationError as exc:
        assert any(error["loc"] == ("currency_code",) for error in exc.errors())
    else:
        raise AssertionError("Invalid currency should be rejected")
