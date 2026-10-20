"""Execute production repository/service/API against disposable SQL tables.

Only these read models' columns are needed; foreign keys are omitted in the
test-owned tables to exercise legacy missing/foreign campaign references. An
explicit CI-only URL enables the same cases on PostgreSQL in an isolated schema.
No default application DATABASE_URL or live environment file is used.
"""
from datetime import UTC, date, datetime
from decimal import Decimal
import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Column, MetaData, Table, create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1.advertising import router
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.ad_campaign import AdCampaign
from app.models.ad_metric import AdMetric
from app.models.order import Order
from app.models.order_item import OrderItem
from app.services.advertising_service import AdvertisingAnalyticsService, AdvertisingServiceError

START = date(2026, 10, 1)
END = date(2026, 10, 2)
STAMP = datetime(2026, 10, 1, tzinfo=UTC)


@pytest.fixture(params=["sqlite", "postgresql"])
def sql_report(request):
    if request.param == "postgresql":
        url = os.getenv("CRM_ATTRIBUTION_TEST_DATABASE_URL")
        if not url:
            pytest.skip("Explicit disposable PostgreSQL test URL required")
        assert url.startswith("postgresql")
        engine = create_engine(url)
        schema = "crm_attribution_test_" + uuid4().hex
    else:
        engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        schema = None
    connection = engine.connect()
    transaction = connection.begin()
    if schema:
        connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        connection = connection.execution_options(schema_translate_map={None: schema})
    metadata = MetaData()
    for model in (AdCampaign, AdMetric, Order, OrderItem):
        Table(model.__tablename__, metadata, *[
            Column(col.name, col.type, primary_key=col.primary_key, nullable=col.nullable)
            for col in model.__table__.columns
        ])
    metadata.create_all(connection)
    db = Session(connection, autoflush=False)
    statements = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(connection, "before_cursor_execute", capture)
    try:
        yield db, statements
    finally:
        db.close()
        transaction.rollback()  # PostgreSQL DDL/schema and fixtures are all transactional.
        connection.close()
        engine.dispose()


def insert(db, model, **values):
    values = {"id": uuid4(), "created_at": STAMP, "updated_at": STAMP, **values}
    db.execute(model.__table__.insert().values(**values))
    return values["id"]


def seed(db):
    workspace, other = uuid4(), uuid4()
    def campaign(name, **extra):
        return insert(db, AdCampaign, workspace_id=workspace, name=name, **extra)
    active = campaign("Synthetic visible")
    archived = campaign("Synthetic archived", status="ARCHIVED")
    order_only = campaign("Synthetic orders only")
    metric_only = campaign("Synthetic metrics only")
    deleted = campaign("Hidden deleted name", deleted_at=STAMP)
    foreign = insert(db, AdCampaign, workspace_id=other, name="Hidden foreign name")
    missing = uuid4()
    def order(status="COMPLETED", payment="PAID", amount=100, **extra):
        values = dict(workspace_id=workspace, campaign_id=active, order_number=uuid4().hex[:20], status=status, payment_status=payment, revenue=amount)
        values.update(extra)
        return insert(db, Order, **values)
    # Every valid lifecycle x payment combination; cancellation has priority.
    for status in ("NEW", "CONFIRMED", "SHIPPED", "DELIVERED", "COMPLETED", "RETURNED", "CANCELLED"):
        for payment in ("PENDING", "PAID", "COD", "REFUNDED"):
            order(status, payment)
    order(campaign_id=archived, amount=200, created_at=datetime(2026, 10, 2, 23, 59, 59, 999999, tzinfo=UTC))
    order(campaign_id=order_only, amount=300, created_at=STAMP)
    for link in (None, deleted, foreign, missing):
        order(campaign_id=link, amount=10000 if link is None else 50)
    order(amount=9999, deleted_at=STAMP)
    order(amount=9999, workspace_id=other)
    order(amount=9999, created_at=datetime(2026, 9, 30, 23, 59, 59, 999999, tzinfo=UTC))
    order(amount=9999, created_at=datetime(2026, 10, 3, tzinfo=UTC))
    # Multiple child items must never multiply aggregate counts/revenue.
    sample = order(amount=400, completed_at=datetime(2027, 1, 1, tzinfo=UTC))
    for _ in range(3):
        insert(db, OrderItem, workspace_id=workspace, order_id=sample, product_variant_id=uuid4(), sku="SYN", product_name="Synthetic", quantity=2, unit_price=1, unit_cost=0, line_total=2, line_cost=0)
    def metric(campaign_id, day=START, **extra):
        values = dict(workspace_id=workspace, campaign_id=campaign_id, metric_date=day, spend=10, orders=9, revenue=900)
        values.update(extra)
        insert(db, AdMetric, **values)
    metric(active)
    metric(active, END, spend=20, source_type="MANUAL")
    metric(archived, spend=40, source_type="CSV_IMPORT")
    metric(metric_only, spend=50)
    metric(active, date(2026, 9, 30), spend=9999)
    metric(active, END, spend=9999, deleted_at=STAMP)
    metric(active, END, spend=9999, workspace_id=other)
    metric(deleted, spend=9999)
    metric(foreign, spend=9999)
    metric(missing, spend=9999)
    return workspace, other, active, archived, order_only, metric_only


def test_real_aggregate_lifecycle_tenants_visibility_and_no_multiplication(sql_report):
    db, statements = sql_report
    workspace, other, active, archived, order_only, metric_only = seed(db)
    statements.clear()
    service = AdvertisingAnalyticsService(db)
    report = service.crm_attribution(workspace, START, END)
    assert len(statements) == 2
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
    rows = {row.campaign_id: row for row in report.campaigns}
    row = rows[active]
    assert (row.placed_orders, row.placed_revenue) == (29, Decimal(3200))
    assert (row.active_orders, row.active_revenue) == (16, Decimal(1900))
    assert row.cancelled_orders == 4
    assert row.returned_refunded_orders == 9
    assert row.active_orders + row.cancelled_orders + row.returned_refunded_orders == row.placed_orders
    assert (row.fulfilled_orders, row.fulfilled_revenue) == (7, Decimal(1000))
    assert (row.paid_fulfilled_orders, row.paid_fulfilled_revenue) == (3, Decimal(600))
    assert (row.spend, row.metric_declared_orders, row.metric_declared_revenue) == (Decimal(30), 18, Decimal(1800))
    assert row.crm_period_revenue_to_spend == Decimal("33.33")
    assert row.cost_per_fulfilled_order == Decimal("4.29")
    assert rows[archived].campaign_status == "ARCHIVED"
    assert rows[archived].fulfilled_revenue == 200
    assert rows[order_only].spend == 0
    assert rows[order_only].crm_period_revenue_to_spend is None
    assert rows[metric_only].placed_orders == 0
    assert rows[metric_only].cost_per_fulfilled_order is None
    assert report.unattributed_orders == 4
    assert report.unattributed.placed_revenue == 10150
    assert report.unattributed.cost_per_fulfilled_order is None
    assert rows[active].fulfilled_revenue == 1000  # Unattributed sales never credit a campaign.
    assert report.totals.placed_orders == 35
    assert report.totals.fulfilled_revenue == 11650
    assert report.totals.spend == 120
    assert report.attributed_orders == 31
    assert report.attribution_coverage_percent == Decimal("88.57")
    assert "Hidden" not in report.model_dump_json()
    assert not any("profit" in name or "customer" in name for name in type(report.totals).model_fields)
    assert service.crm_attribution(uuid4(), START, END).totals.placed_orders == 0
    empty = service.crm_attribution(workspace, date(2025, 1, 1), date(2025, 1, 2))
    assert not empty.campaigns
    assert empty.attribution_coverage_percent is None
    assert empty.totals.crm_period_revenue_to_spend is None
    assert empty.totals.cost_per_fulfilled_order is None


def user(workspace, role="ANALYST"):
    return SimpleNamespace(id=uuid4(), workspaces=[SimpleNamespace(workspace_id=workspace, is_active=True, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name=role))])


def test_real_api_workspace_headers_rbac_dates_and_read_only(sql_report):
    db, statements = sql_report
    workspace, other, *_ = seed(db)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    actor = user(workspace)
    app.dependency_overrides[get_current_user] = lambda: actor
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        headers = {"X-Workspace-ID": str(workspace)}
        statements.clear()
        response = client.get("/api/v1/advertising/crm-attribution?start_date=2026-10-01&end_date=2026-10-02", headers=headers)
        assert response.status_code == 200
        assert response.json()["totals"]["placed_orders"] == 35
        assert response.json()["source"] == "crm_manual_campaign_link"
        assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
        assert client.get("/api/v1/advertising/crm-attribution").status_code == 400
        assert client.get("/api/v1/advertising/crm-attribution", headers={"X-Workspace-ID": str(other)}).status_code == 403
        actor.workspaces[0].is_active = False
        assert client.get("/api/v1/advertising/crm-attribution", headers=headers).status_code == 403
        actor.workspaces[0].is_active = True
        for role in ("OWNER", "MANAGER", "ANALYST"):
            actor.workspaces[0].role.name = role
            assert client.get("/api/v1/advertising/crm-attribution?start_date=2026-10-01&end_date=2026-10-02", headers=headers).status_code == 200
        assert client.get("/api/v1/advertising/crm-attribution?start_date=bad", headers=headers).status_code == 422
        assert client.get("/api/v1/advertising/crm-attribution?start_date=2026-10-03&end_date=2026-10-01", headers=headers).status_code == 400
        assert client.get("/api/v1/advertising/crm-attribution?end_date=9999-12-31", headers=headers).status_code == 400
        assert client.get("/api/v1/advertising/crm-attribution?end_date=0001-01-01", headers=headers).status_code == 400
    unauthenticated = FastAPI()
    unauthenticated.include_router(router)
    with TestClient(unauthenticated) as client:
        assert client.get("/advertising/crm-attribution", headers=headers).status_code == 401


def test_invalid_period_never_queries():
    class NoReads:
        def execute(self, *args, **kwargs):
            raise AssertionError("invalid period must not query")
    service = AdvertisingAnalyticsService(NoReads())
    with pytest.raises(AdvertisingServiceError):
        service.crm_attribution(uuid4(), END, START)
