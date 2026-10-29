from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.api.v1 import subscriptions as routes
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.role import RoleName
from app.models.workspace_subscription import SubscriptionStatus, WorkspaceSubscription
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.subscription import SubscriptionDisplayStatus, SubscriptionStatusResponse
from app.services.subscription_service import SubscriptionAccessError, SubscriptionService, describe_subscription

START = datetime(2026, 10, 1, tzinfo=UTC)
END = datetime(2026, 11, 1, tzinfo=UTC)


def term(workspace_id, status=SubscriptionStatus.ACTIVE, **changes):
    values = dict(workspace_id=workspace_id, plan_code="pilot", status=status.value,
                  current_period_start=START, current_period_end=END, cancel_at_period_end=False)
    values.update(changes)
    return WorkspaceSubscription(**values)


@pytest.mark.parametrize("stored", [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING])
@pytest.mark.parametrize("instant,expected,valid", [
    (START - timedelta(microseconds=1), "PENDING", False),
    (START, None, True),
    (END - timedelta(microseconds=1), None, True),
    (END, "EXPIRED", False),
    (END + timedelta(days=1), "EXPIRED", False),
])
def test_term_is_start_inclusive_and_end_exclusive(stored, instant, expected, valid):
    workspace = uuid4()
    result = describe_subscription(workspace, term(workspace, stored), now=instant)
    assert result.status.value == (expected or stored.value)
    assert result.has_current_term is valid
    assert result.enforcement_enabled is False


@pytest.mark.parametrize("stored", [SubscriptionStatus.PENDING, SubscriptionStatus.PAST_DUE,
                                    SubscriptionStatus.CANCELED, SubscriptionStatus.EXPIRED])
def test_non_entitled_states_do_not_grant_a_term(stored):
    workspace = uuid4()
    result = describe_subscription(workspace, term(workspace, stored), now=START)
    assert result.status.value == stored.value
    assert result.has_current_term is False


def test_cancel_at_period_end_retains_only_the_remaining_term_and_does_not_write():
    workspace = uuid4()
    record = term(workspace, cancel_at_period_end=True)
    assert describe_subscription(workspace, record, now=START).has_current_term
    assert not describe_subscription(workspace, record, now=END).has_current_term
    assert record.status == "ACTIVE"
    assert record.cancel_at_period_end is True


def test_timezone_offsets_represent_the_same_instant():
    workspace = uuid4()
    offset = timezone(timedelta(hours=3))
    record = term(workspace, current_period_start=START.astimezone(offset), current_period_end=END.astimezone(offset))
    result = describe_subscription(workspace, record, now=END.astimezone(offset))
    assert result.status == SubscriptionDisplayStatus.EXPIRED
    assert result.current_period_start == START
    assert result.current_period_end == END


@pytest.mark.parametrize("field", ["now", "current_period_start", "current_period_end"])
def test_naive_timestamps_cannot_report_an_entitlement(field):
    workspace = uuid4()
    changes = {field: START.replace(tzinfo=None)} if field != "now" else {}
    with pytest.raises(ValueError, match="timezone"):
        describe_subscription(workspace, term(workspace, **changes), now=START.replace(tzinfo=None) if field == "now" else START)


def test_foreign_record_is_rejected_even_if_a_repository_returns_it():
    with pytest.raises(SubscriptionAccessError):
        describe_subscription(uuid4(), term(uuid4()), now=START)


def test_invalid_period_cannot_report_an_entitlement():
    workspace = uuid4()
    with pytest.raises(ValueError, match="positive duration"):
        describe_subscription(workspace, term(workspace, current_period_end=START), now=START)


def service_for(membership, subscription=None):
    service = SubscriptionService.__new__(SubscriptionService)
    service.workspaces = SimpleNamespace(get_active_membership=lambda workspace, user: membership)
    reads = []
    service.subscriptions = SimpleNamespace(get_for_workspace=lambda workspace: reads.append(workspace) or subscription)
    return service, reads


def test_legacy_paid_looking_plan_does_not_enroll_or_grant_paid_access():
    workspace, user = uuid4(), uuid4()
    membership = SimpleNamespace(role=SimpleNamespace(name="OWNER"), workspace=SimpleNamespace(subscription_plan="enterprise"))
    service, reads = service_for(membership)
    result = service.get_status(workspace, user)
    assert reads == [workspace]
    assert result.status == SubscriptionDisplayStatus.UNMANAGED
    assert result.plan_code is None and result.current_period_end is None
    assert not result.has_current_term and not result.enforcement_enabled


@pytest.mark.parametrize("role", [None, "MANAGER", "ANALYST"])
def test_service_rejects_before_reading_subscription(role):
    membership = None if role is None else SimpleNamespace(role=SimpleNamespace(name=role))
    service, reads = service_for(membership)
    with pytest.raises(SubscriptionAccessError):
        service.get_status(uuid4(), uuid4())
    assert reads == []


def test_repository_binds_requested_workspace_in_its_query():
    workspace = uuid4()
    statements = []
    db = SimpleNamespace(execute=lambda statement: statements.append(statement) or SimpleNamespace(scalar_one_or_none=lambda: None))
    assert SubscriptionRepository(db).get_for_workspace(workspace) is None
    query = statements[0].compile(dialect=postgresql.dialect())
    assert query.params == {"workspace_id_1": workspace}
    assert "workspace_subscriptions.workspace_id =" in str(query)


@pytest.mark.parametrize("role,member_active,workspace_active,foreign,expected", [
    ("OWNER", True, True, False, 200),
    ("MANAGER", True, True, False, 403),
    ("ANALYST", True, True, False, 403),
    ("OWNER", False, True, False, 403),
    ("OWNER", True, False, False, 403),
    ("OWNER", True, True, True, 403),
])
def test_http_read_requires_owner_in_the_active_selected_workspace(monkeypatch, role, member_active, workspace_active, foreign, expected):
    workspace, user_id = uuid4(), uuid4()
    user = SimpleNamespace(id=user_id, workspaces=[SimpleNamespace(
        workspace_id=uuid4() if foreign else workspace,
        role=SimpleNamespace(name=role), is_active=member_active,
        workspace=SimpleNamespace(is_active=workspace_active),
    )])
    reads = []
    def status(workspace_id, actor):
        reads.append((workspace_id, actor))
        return SubscriptionStatusResponse(workspace_id=workspace_id, status=SubscriptionDisplayStatus.UNMANAGED)
    monkeypatch.setattr(routes, "SubscriptionService", lambda db: SimpleNamespace(get_status=status))
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: None
    response = TestClient(app).get("/api/v1/workspaces/current/subscription", headers={"X-Workspace-ID": str(workspace)})
    assert response.status_code == expected
    if expected == 200:
        assert reads == [(workspace, user_id)]
        assert response.headers["Cache-Control"] == "no-store"
        assert response.json()["enforcement_enabled"] is False
    else:
        assert reads == []


def test_http_missing_workspace_is_rejected():
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(workspaces=[])
    app.dependency_overrides[get_db] = lambda: None
    assert TestClient(app).get("/api/v1/workspaces/current/subscription").status_code == 400
