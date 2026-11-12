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
from app.models.customer import Customer
from app.models.platform_admin import PlatformAuditEvent, PlatformGrant, PlatformRole
from app.models.order import Order
from app.models.product import Product
from app.models.product_usage import DROPPED_EVENTS, ProductUsageDaily, ProductUsageEvent, UsageEvent, UsageSource
from app.models.product_variant import ProductVariant
from app.models.role import Role
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_subscription import WorkspaceSubscription
from app.models.workspace_user import WorkspaceUser
from app.repositories.audit_log_repository import DEMO_WORKSPACE_CREATE_ACTION
from app.services.platform_grant_service import PlatformGrantService
from app.repositories.product_usage_repository import ProductUsageRepository
from app.schemas.order import OrderCreate, OrderItemCreate
from app.schemas.product import ProductCreate
from app.schemas.workspace import WorkspaceCreate
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.product_usage_service import ProductUsageService, ProductUsageWriter
from app.services.workspace_service import WorkspaceService

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


@pytest.fixture
def capture_enabled(monkeypatch):
    now = datetime.now(UTC)
    monkeypatch.setattr(get_settings(), "product_usage_capture_enabled", True)
    monkeypatch.setattr(get_settings(), "product_usage_coverage_from", now - timedelta(days=45))
    return now


def test_product_usage_crm_producers_record_milestones_and_exclude_demo_and_imports(db, capture_enabled):
    owner = add_user(db)
    if db.scalar(select(Role.id).where(Role.name == "OWNER")) is None:
        db.add(Role(name="OWNER"))
        db.flush()
    workspace_id = WorkspaceService(db).create_workspace(
        WorkspaceCreate(name="Usage shop", slug=f"usage-{uuid4().hex}"), owner.id,
    ).workspace_id
    demo = add_workspace(db, "Demo excluded from usage", demo=True)
    product_service = ProductService(db)
    first = product_service.create_product(workspace_id, ProductCreate(name="First product"), owner.id)
    product_service.create_product(workspace_id, ProductCreate(name="Second product"), owner.id)
    product_service.create_product(demo.id, ProductCreate(name="Synthetic demo"), owner.id)
    variant = ProductVariant(workspace_id=workspace_id, product_id=first.id, sku="SA3-TEST")
    customer = Customer(workspace_id=workspace_id, name="Synthetic buyer")
    db.add_all([variant, customer])
    db.flush()
    payload = OrderCreate(
        customer_id=customer.id,
        items=[OrderItemCreate(product_variant_id=variant.id, quantity=1, unit_price=10)],
    )
    order_service = OrderService(db)
    order_service.create(workspace_id, payload.model_copy(update={"is_historical": True}), owner.id, affect_inventory=False)
    order = order_service.create(workspace_id, payload, owner.id, affect_inventory=False)
    order_service.create(workspace_id, payload, owner.id, affect_inventory=False)
    writer = ProductUsageWriter(db)
    writer.order_created(workspace_id, order.id)
    writer.integration_used(workspace_id, UsageSource.NOVA_POSHTA)
    writer.integration_used(workspace_id, UsageSource.NOVA_POSHTA)
    writer.integration_used(workspace_id, UsageSource.META_ADS)
    db.commit()

    report = ProductUsageService(db).get_report(7, workspace_id=workspace_id)
    assert report.coverage == "complete"
    assert report.totals.model_dump() == {
        "active_workspaces": 1, "active_workspace_days": 1, "activated_workspaces": 1,
        "first_products": 1, "first_orders": 1, "orders_created": 2, "integration_days": 2,
    }
    events = db.scalars(select(ProductUsageEvent).where(ProductUsageEvent.workspace_id == workspace_id)).all()
    assert len(events) == 7
    assert all(event.source_key != customer.id.hex for event in events)
    assert not db.scalar(select(ProductUsageEvent.id).where(ProductUsageEvent.workspace_id == demo.id))
    assert ProductUsageService(db).get_report(7, workspace_id=demo.id).totals is None

    with db.begin_nested() as operation:
        pending = order_service.create(workspace_id, payload, owner.id, affect_inventory=False, commit=False)
        pending_id = pending.id
        assert db.scalar(select(ProductUsageEvent.id).where(ProductUsageEvent.source_key == pending_id.hex))
        operation.rollback()
    assert db.get(Order, pending_id) is None
    assert not db.scalar(select(ProductUsageEvent.id).where(ProductUsageEvent.source_key == pending_id.hex))
    assert ProductUsageService(db).get_report(7, workspace_id=workspace_id).totals.orders_created == 2


def test_product_usage_failure_does_not_block_product_commit(db, capture_enabled, monkeypatch):
    workspace = add_workspace(db, "Usage failure shop")
    increment = ProductUsageRepository.increment_daily

    def fail_aggregate(self, workspace_id, day, event):
        if event != DROPPED_EVENTS:
            self.db.execute(text("SELECT 1 / 0"))
        return increment(self, workspace_id, day, event)

    monkeypatch.setattr(ProductUsageRepository, "increment_daily", fail_aggregate)
    product = ProductService(db).create_product(workspace.id, ProductCreate(name="Committed product"), None)
    assert db.get(Product, product.id).name == "Committed product"
    assert not db.scalar(select(ProductUsageEvent.id).where(ProductUsageEvent.workspace_id == workspace.id))
    report = ProductUsageService(db).get_report(7, workspace_id=workspace.id)
    assert report.coverage == "partial" and report.dropped_operations == 1
    assert report.totals.active_workspaces == 0


def test_product_usage_windows_and_workspace_boundaries(client, db, capture_enabled, monkeypatch):
    now = capture_enabled
    admin = add_user(db, PlatformRole.ADMIN)
    owner = add_user(db)
    first = add_workspace(db, "Usage first shop")
    second = add_workspace(db, "Usage second shop")
    add_member(db, first, owner, "OWNER")
    repo = ProductUsageRepository(db)
    for workspace_id, ages in ((first.id, (0, 6, 7, 29, 30)), (second.id, (0, 8))):
        for age in ages:
            repo.record(workspace_id, UsageEvent.ORDER_CREATED, UsageSource.ORDERS, uuid4().hex, now - timedelta(days=age))
    repo.record(first.id, UsageEvent.FIRST_PRODUCT, UsageSource.CATALOG, first.id.hex, now)
    db.commit()

    auth = login(client, admin)
    summary_url = f"{PREFIX}/activity/summary"
    first_url = f"{PREFIX}/workspaces/{first.id}/activity"
    second_url = f"{PREFIX}/workspaces/{second.id}/activity"
    overall = client.get(summary_url, params={"days": 7}, headers=auth).json()
    assert overall["coverage"] == "complete"
    assert overall["totals"]["active_workspaces"] == 2
    assert overall["totals"]["active_workspace_days"] == 3
    assert overall["totals"]["orders_created"] == 3
    assert client.get(first_url, params={"days": 30}, headers={**auth, "X-Workspace-ID": str(second.id)}).json()["totals"]["orders_created"] == 4
    assert client.get(second_url, headers=auth).json()["totals"]["first_products"] == 0
    assert client.get(first_url, headers=auth).json()["totals"]["orders_created"] == 2
    assert client.get(summary_url, params={"days": 8}, headers=auth).status_code == 422
    assert client.get(f"{PREFIX}/workspaces/{uuid4()}/activity", headers=auth).status_code == 404
    assert client.get(first_url, headers=login(client, owner)).status_code == 403
    assert client.get(summary_url, headers=login(client, add_user(db, PlatformRole.AUDITOR))).status_code == 403
    assert client.get(summary_url, headers=login(client, add_user(db, PlatformRole.SUPPORT))).status_code == 200

    monkeypatch.setattr(get_settings(), "product_usage_coverage_from", now - timedelta(days=3))
    partial = ProductUsageService(db).get_report(7, workspace_id=first.id, now=now)
    assert partial.coverage == "partial" and partial.totals.orders_created == 1
    monkeypatch.setattr(get_settings(), "product_usage_capture_enabled", False)
    before = db.scalar(select(ProductUsageDaily.event_count).where(
        ProductUsageDaily.workspace_id == first.id, ProductUsageDaily.day == now.date(),
        ProductUsageDaily.event_type == UsageEvent.ORDER_CREATED,
    ))
    ProductUsageWriter(db).order_created(first.id, uuid4())
    assert db.scalar(select(ProductUsageDaily.event_count).where(
        ProductUsageDaily.workspace_id == first.id, ProductUsageDaily.day == now.date(),
        ProductUsageDaily.event_type == UsageEvent.ORDER_CREATED,
    )) == before
    unavailable = client.get(summary_url, headers=auth).json()
    assert unavailable["coverage"] == "unavailable" and unavailable["totals"] is None
    assert db.execute(text("""
        SELECT count(*) FROM pg_class WHERE oid IN (
            'public.product_usage_events'::regclass, 'public.product_usage_daily'::regclass
        ) AND relrowsecurity
    """)).scalar_one() == 2
