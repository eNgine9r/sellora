"""Exercise the platform API using the explicitly isolated PostgreSQL canary."""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.auth.password import hash_password
from app.core.config import get_settings
from app.database.session import get_db
from app.main import app
from app.models.audit_log import AuditLog
from app.models.platform_admin import PlatformAuditEvent, PlatformGrant, PlatformRole
from app.models.role import Role
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_subscription import WorkspaceSubscription
from app.models.workspace_user import WorkspaceUser
from app.repositories.audit_log_repository import DEMO_WORKSPACE_CREATE_ACTION
from app.services.platform_grant_service import PlatformGrantService

pytestmark = pytest.mark.skipif(
    os.getenv("SELLORA_PLATFORM_ADMIN_DISPOSABLE_CANARY") != "YES",
    reason="explicit disposable platform admin database required",
)
PREFIX = "/api/v1/platform-admin"
ORIGIN = {"Origin": "http://localhost:3000"}
PASSWORD = "Synthetic-Platform-Password1"


@pytest.fixture
def db():
    url = make_url(os.environ["DATABASE_URL"])
    assert url.database == "sellora_platform_admin_canary_isolated"
    engine = create_engine(url)
    with engine.connect() as connection, connection.begin() as transaction:
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()
    engine.dispose()


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "platform_admin_enabled", True)
    monkeypatch.setattr(get_settings(), "cookie_sessions_enabled", True)
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def add_user(db, platform_role=None, **kwargs):
    account = User(
        email=f"platform-{uuid4().hex}@example.com", password_hash=hash_password(PASSWORD),
        first_name="Synthetic", last_name="Operator", **kwargs,
    )
    db.add(account)
    db.flush()
    if platform_role:
        db.add(PlatformGrant(user_id=account.id, role=platform_role))
        db.flush()
    return account


def add_workspace(db, name, *, active=True, demo=False, created_at=None):
    workspace = Workspace(name=name, slug=f"platform-{uuid4().hex}", is_active=active)
    if created_at:
        workspace.created_at = created_at
    db.add(workspace)
    db.flush()
    if demo:
        db.add(AuditLog(
            workspace_id=workspace.id, entity_type="Workspace", entity_id=str(workspace.id),
            action=DEMO_WORKSPACE_CREATE_ACTION,
        ))
        db.flush()
    return workspace


def add_member(db, workspace, user, role_name, *, active=True):
    role = db.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        role = Role(name=role_name)
        db.add(role)
        db.flush()
    db.add(WorkspaceUser(workspace_id=workspace.id, user_id=user.id, role_id=role.id, is_active=active))
    db.flush()


def login(client, user):
    response = client.post("/api/v1/auth/session/login", json={"email": user.email, "password": PASSWORD}, headers=ORIGIN)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_platform_grants_are_independent_of_tenant_roles_and_headers(client, db, monkeypatch):
    workspace = add_workspace(db, "Synthetic tenant")
    other = add_workspace(db, "Synthetic second tenant")
    admin = add_user(db, PlatformRole.ADMIN)
    admin_auth = login(client, admin)
    for role in ("OWNER", "MANAGER", "ANALYST"):
        user = add_user(db)
        add_member(db, workspace, user, role)
        denied = client.get(f"{PREFIX}/workspaces/{other.id}", headers={**login(client, user), "X-Workspace-ID": str(workspace.id)})
        assert denied.status_code == 403
        assert denied.headers["cache-control"] == "private, no-store"

    me = client.get(f"{PREFIX}/me", headers=admin_auth)
    assert me.json()["role"] == "PLATFORM_ADMIN"
    assert client.get(f"{PREFIX}/workspaces/{other.id}", headers={**admin_auth, "X-Workspace-ID": str(workspace.id)}).json()["id"] == str(other.id)
    assert client.get("/api/v1/workspaces/current/subscription", headers={**admin_auth, "X-Workspace-ID": str(other.id)}).status_code == 403
    assert client.get(f"{PREFIX}/me").status_code == 401
    assert client.get(f"{PREFIX}/me", headers={"Authorization": "Bearer invalid"}).status_code == 401

    auditor = add_user(db, PlatformRole.AUDITOR)
    auditor_auth = login(client, auditor)
    assert client.get(f"{PREFIX}/me", headers=auditor_auth).json()["capabilities"] == ["platform.access"]
    assert client.get(f"{PREFIX}/summary", headers=auditor_auth).status_code == 403

    monkeypatch.setattr(get_settings(), "platform_admin_enabled", False)
    assert client.get(f"{PREFIX}/me", headers=admin_auth).status_code == 404


def test_legacy_upgrade_refresh_and_revocation(client, db):
    admin = add_user(db, PlatformRole.ADMIN)
    legacy_headers = {"Authorization": f"Bearer {create_access_token(admin.id)}"}
    assert client.get(f"{PREFIX}/me", headers=legacy_headers).status_code == 401
    upgraded = client.post("/api/v1/auth/session/upgrade", headers={**legacy_headers, **ORIGIN})
    assert upgraded.status_code == 200, upgraded.text
    upgraded_headers = {"Authorization": f"Bearer {upgraded.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=upgraded_headers).status_code == 200
    assert client.get(f"{PREFIX}/me", headers=upgraded_headers).status_code == 401

    login(client, admin)
    refreshed = client.post("/api/v1/auth/session/refresh", headers=ORIGIN)
    assert refreshed.status_code == 200, refreshed.text
    auth = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
    assert client.get(f"{PREFIX}/me", headers=auth).status_code == 200
    assert client.post("/api/v1/auth/session/logout", headers=ORIGIN).status_code == 204
    assert client.get(f"{PREFIX}/me", headers=auth).status_code == 401

    auth = login(client, admin)
    db.get(PlatformGrant, admin.id).revoked_at = datetime.now(UTC)
    db.commit()
    assert client.get(f"{PREFIX}/me", headers=auth).status_code == 403


def test_workspace_directory_and_subscription_return_only_scoped_projections(client, db):
    now = datetime.now(UTC)
    first = add_workspace(db, "Platform Search Match A", created_at=now)
    second = add_workspace(db, "Platform Search Match B", active=False, demo=True, created_at=now)
    support = add_user(db, PlatformRole.SUPPORT)
    active_member = add_user(db)
    disabled_member = add_user(db, is_active=False)
    add_member(db, first, active_member, "OWNER")
    add_member(db, first, disabled_member, "MANAGER")
    add_member(db, second, active_member, "OWNER")
    db.add(WorkspaceSubscription(
        workspace_id=first.id, plan_code="pilot", status="ACTIVE",
        current_period_start=now - timedelta(days=1), current_period_end=now + timedelta(days=1),
    ))
    db.flush()
    auth = login(client, support)
    filters = {"q": "Platform Search Match", "limit": 1}
    page_response = client.get(f"{PREFIX}/workspaces", params=filters, headers=auth)
    assert page_response.status_code == 200, page_response.text
    page = page_response.json()
    second_page = client.get(
        f"{PREFIX}/workspaces", params={**filters, "cursor": page["next_cursor"]}, headers=auth,
    ).json()
    assert {page["items"][0]["id"], second_page["items"][0]["id"]} == {str(first.id), str(second.id)}
    assert second_page["next_cursor"] is None
    assert client.get(
        f"{PREFIX}/workspaces", params={**filters, "active": "true", "cursor": page["next_cursor"]}, headers=auth,
    ).status_code == 422
    demo_page = client.get(f"{PREFIX}/workspaces", params={"active": "false", "demo": "true"}, headers=auth).json()
    assert [item["id"] for item in demo_page["items"]] == [str(second.id)]
    detail = client.get(f"{PREFIX}/workspaces/{first.id}", headers=auth).json()
    assert detail["active_member_count"] == 1 and detail["subscription"]["plan_code"] == "pilot"
    assert set(detail) == {"id", "name", "slug", "is_active", "is_demo", "created_at", "subscription",
                           "currency_code", "timezone", "active_member_count"}
    assert active_member.email not in str(detail)
    unmanaged = client.get(f"{PREFIX}/workspaces/{second.id}/subscription", headers=auth).json()
    assert unmanaged["status"] == "UNMANAGED" and unmanaged["enforcement_enabled"] is False
    assert client.get(f"{PREFIX}/workspaces/{uuid4()}/subscription", headers=auth).status_code == 404
    summary = client.get(f"{PREFIX}/summary", headers=auth).json()
    assert summary["total_workspaces"] == 2
    assert summary["enabled_workspaces"] == summary["demo_workspaces"] == summary["workspaces_with_current_term"] == 1
    event = db.scalar(select(PlatformAuditEvent).where(PlatformAuditEvent.action == "READ_WORKSPACE"))
    assert event.workspace_id == first.id and event.actor_user_id == support.id
    assert event.outcome == "ALLOWED"


def test_grant_lifecycle_and_audit_immutability(db):
    admin, support = add_user(db), add_user(db)
    service = PlatformGrantService(db)
    service.change(actor_id=admin.id, password=PASSWORD, target_id=admin.id, action="BOOTSTRAP", approval_ref="QA-1")
    with pytest.raises(PermissionError):
        service.change(actor_id=support.id, password=PASSWORD, target_id=support.id, action="BOOTSTRAP", approval_ref="QA-1")
    service.change(actor_id=admin.id, password=PASSWORD, target_id=support.id, action="GRANT",
                   role=PlatformRole.SUPPORT, approval_ref="QA-2")
    service.change(actor_id=admin.id, password=PASSWORD, target_id=support.id, action="REVOKE", approval_ref="QA-3")
    assert db.get(PlatformGrant, support.id).revoked_at is not None
    assert db.execute(text("""
        SELECT count(*) FROM pg_class WHERE oid IN (
            'public.platform_operator_grants'::regclass, 'public.platform_audit_events'::regclass
        ) AND relrowsecurity
    """)).scalar_one() == 2
    with pytest.raises(Exception, match="append-only"):
        with db.begin_nested():
            db.execute(text("DELETE FROM public.platform_audit_events"))
