"""Real order-update schema/service/API on disposable SQL, no live DB.

These tables retain production column types/defaults while omitting foreign-key
constraints so foreign/legacy links can be seeded. API dependencies open/close a
real Session per request, matching production rollback-on-close behavior.
"""
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Column, JSON, MetaData, Table, create_engine, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1.advertising import router as advertising_router
from app.api.v1.orders import router as orders_router
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.ad_campaign import AdCampaign
from app.models.ad_metric import AdMetric
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransaction
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order_status_history import OrderStatusHistory
from app.schemas.order import OrderUpdate
from app.services.order_service import OrderService

STAMP = datetime(2026, 10, 19, 10, tzinfo=UTC)
MODELS = (AdCampaign, AdMetric, AuditLog, Customer, Inventory, InventoryTransaction, Order, OrderItem, OrderStatusHistory)
FINANCIAL_FIELDS = ("revenue", "product_cost", "ad_cost", "shipping_cost", "cod_fee", "other_cost", "net_profit")


def insert(db, model, **values):
    fields = {"id": uuid4(), **values}
    if "created_at" in model.__table__.columns:
        fields.setdefault("created_at", STAMP)
    if "updated_at" in model.__table__.columns:
        fields.setdefault("updated_at", STAMP)
    db.execute(model.__table__.insert().values(**fields))
    return fields["id"]


@pytest.fixture
def campaign_editor():
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    metadata = MetaData()
    for model in MODELS:
        Table(model.__tablename__, metadata, *[
            Column(c.name, JSON() if isinstance(c.type, JSONB) else c.type,
                   primary_key=c.primary_key, nullable=c.nullable, server_default=c.server_default)
            for c in model.__table__.columns
        ])
    metadata.create_all(engine)
    workspace, foreign_workspace = uuid4(), uuid4()
    with Session(engine) as db:
        customer = insert(db, Customer, workspace_id=workspace, name="Synthetic customer")
        second_customer = insert(db, Customer, workspace_id=workspace, name="Synthetic alternative")
        active = insert(db, AdCampaign, workspace_id=workspace, name="Synthetic A")
        other = insert(db, AdCampaign, workspace_id=workspace, name="Synthetic B")
        archived = insert(db, AdCampaign, workspace_id=workspace, name="Synthetic archived", status="ARCHIVED")
        deleted = insert(db, AdCampaign, workspace_id=workspace, name="Hidden deleted", deleted_at=STAMP)
        foreign = insert(db, AdCampaign, workspace_id=foreign_workspace, name="Hidden foreign")
        order = insert(db, Order, workspace_id=workspace, order_number="SYN-CAMPAIGN", customer_id=customer,
                       status="COMPLETED", payment_status="PAID", revenue=100, product_cost=20,
                       ad_cost=5, shipping_cost=3, cod_fee=2, other_cost=1, net_profit=69)
        foreign_order = insert(db, Order, workspace_id=foreign_workspace, order_number="SYN-FOREIGN",
                               status="NEW", payment_status="PENDING", revenue=0)
        variant = uuid4()
        item = insert(db, OrderItem, workspace_id=workspace, order_id=order, product_variant_id=variant,
                      sku="SYN", product_name="Synthetic product", quantity=2, unit_price=50,
                      unit_cost=10, line_total=100, line_cost=20)
        inventory = insert(db, Inventory, workspace_id=workspace, product_variant_id=variant,
                           stock_quantity=18, reserved_quantity=0)
        for campaign in (active, other, archived):
            insert(db, AdMetric, workspace_id=workspace, campaign_id=campaign,
                   metric_date=date(2026, 10, 19), spend=10)
        db.commit()
    actor = SimpleNamespace(id=uuid4(), workspaces=[SimpleNamespace(
        workspace_id=workspace, is_active=True, workspace=SimpleNamespace(is_active=True),
        role=SimpleNamespace(name="MANAGER"),
    )])
    app = FastAPI()
    app.include_router(orders_router, prefix="/api/v1")
    app.include_router(advertising_router, prefix="/api/v1")

    def isolated_db():
        with Session(engine, autoflush=False) as db:
            yield db
    app.dependency_overrides[get_db] = isolated_db
    app.dependency_overrides[get_current_user] = lambda: actor
    with TestClient(app) as client:
        yield SimpleNamespace(engine=engine, client=client, actor=actor, workspace=workspace,
                              foreign_workspace=foreign_workspace, customer=customer, second_customer=second_customer,
                              active=active, other=other, archived=archived, deleted=deleted, foreign=foreign,
                              order=order, foreign_order=foreign_order, item=item, inventory=inventory)
    engine.dispose()


def stored(case):
    # A fresh Session prevents an identity-map success from standing in for persistence.
    with Session(case.engine) as db:
        order = db.execute(select(Order).where(Order.id == case.order)).scalar_one()
        item = db.execute(select(OrderItem).where(OrderItem.id == case.item)).scalar_one()
        inventory = db.execute(select(Inventory).where(Inventory.id == case.inventory)).scalar_one()
        return {
            "campaign": order.campaign_id, "customer": order.customer_id,
            "status": order.status, "payment": order.payment_status, "notes": order.notes,
            "finance": tuple(getattr(order, key) for key in FINANCIAL_FIELDS),
            "item": (item.id, item.product_variant_id, item.quantity, item.unit_price, item.unit_cost, item.line_total, item.line_cost),
            "inventory": (inventory.stock_quantity, inventory.reserved_quantity),
            "transactions": db.scalar(select(func.count()).select_from(InventoryTransaction)),
            "history": db.scalar(select(func.count()).select_from(OrderStatusHistory)),
            "audit": db.scalar(select(func.count()).select_from(AuditLog)),
        }


def headers(case):
    return {"X-Workspace-ID": str(case.workspace)}


def report(case):
    response = case.client.get("/api/v1/advertising/crm-attribution?start_date=2026-10-19&end_date=2026-10-19",
                               headers=headers(case))
    assert response.status_code == 200
    return response.json()


def assert_report_bucket(case, expected_campaign, baseline_totals):
    result = report(case)
    assert result["totals"] == baseline_totals
    assert result["attributed_orders"] == (1 if expected_campaign else 0)
    assert result["unattributed_orders"] == (0 if expected_campaign else 1)
    assert Decimal(result["unattributed"]["placed_revenue"]) == (0 if expected_campaign else 100)
    for row in result["campaigns"]:
        credited = row["campaign_id"] == (str(expected_campaign) if expected_campaign else None)
        assert row["placed_orders"] == row["fulfilled_orders"] == int(credited)
        assert Decimal(row["placed_revenue"]) == Decimal(row["fulfilled_revenue"]) == (100 if credited else 0)
    if expected_campaign == case.archived:
        assert next(row for row in result["campaigns"] if row["campaign_id"] == str(case.archived))["campaign_status"] == "ARCHIVED"


def test_update_schema_distinguishes_omit_nullable_and_typed_campaign():
    assert "campaign_id" not in OrderUpdate.model_validate({}).model_fields_set
    clear = OrderUpdate.model_validate({"campaign_id": None})
    assert clear.model_dump(exclude_unset=True) == {"campaign_id": None}
    identity = uuid4()
    assign = OrderUpdate.model_validate({"campaign_id": str(identity)})
    assert assign.campaign_id == identity
    assert assign.model_dump(exclude_unset=True) == {"campaign_id": identity}


def test_actual_editor_api_assign_reassign_archive_omit_and_clear_move_report_only(campaign_editor):
    c = campaign_editor
    baseline = stored(c)
    totals = report(c)["totals"]
    assert_report_bucket(c, None, totals)
    for expected, name in [(c.active, "Synthetic A"), (c.other, "Synthetic B"), (c.archived, "Synthetic archived")]:
        # Same locked-order editor metadata shape; no item/status command.
        payload = {"campaign_id": str(expected), "customer_id": str(c.customer),
                   "payment_status": "PAID", "ad_cost": "5", "shipping_cost": "3",
                   "cod_fee": "2", "other_cost": "1", "notes": None}
        response = c.client.put(f"/api/v1/orders/{c.order}", headers=headers(c), json=payload)
        assert response.status_code == 200
        assert response.json()["campaign_id"] == str(expected)
        assert response.json()["campaign_name"] == name
        snapshot = stored(c)
        assert snapshot["campaign"] == expected
        assert snapshot["audit"] == baseline["audit"] + 1
        assert {key: value for key, value in snapshot.items() if key not in {"campaign", "audit"}} == {
            key: value for key, value in baseline.items() if key not in {"campaign", "audit"}
        }
        baseline = snapshot
        readback = c.client.get(f"/api/v1/orders/{c.order}", headers=headers(c))
        assert readback.status_code == 200 and readback.json()["campaign_id"] == str(expected)
        assert_report_bucket(c, expected, totals)
    response = c.client.put(f"/api/v1/orders/{c.order}", headers=headers(c), json={"notes": "Synthetic omitted campaign"})
    assert response.status_code == 200 and response.json()["campaign_id"] == str(c.archived)
    assert stored(c)["campaign"] == c.archived
    assert_report_bucket(c, c.archived, totals)
    response = c.client.put(f"/api/v1/orders/{c.order}", headers=headers(c), json={"campaign_id": None})
    assert response.status_code == 200 and response.json()["campaign_id"] is None and response.json()["campaign_name"] is None
    assert stored(c)["campaign"] is None
    assert_report_bucket(c, None, totals)
    snapshot = stored(c)
    assert snapshot["finance"] == baseline["finance"]
    assert snapshot["item"] == baseline["item"] and snapshot["inventory"] == baseline["inventory"]
    assert snapshot["transactions"] == baseline["transactions"] == 0


@pytest.mark.parametrize("kind", ["foreign", "missing", "deleted", "malformed"])
def test_invalid_campaign_editor_payload_cannot_persist_any_mutation(campaign_editor, kind):
    c = campaign_editor
    assert c.client.put(f"/api/v1/orders/{c.order}", headers=headers(c), json={"campaign_id": str(c.active)}).status_code == 200
    baseline, before_report = stored(c), report(c)
    invalid = "not-a-uuid" if kind == "malformed" else str(uuid4() if kind == "missing" else getattr(c, kind))
    response = c.client.put(f"/api/v1/orders/{c.order}", headers=headers(c), json={
        "campaign_id": invalid, "customer_id": str(c.second_customer), "notes": "Must roll back",
        "shipping_cost": "999",
    })
    assert response.status_code == 422
    assert stored(c) == baseline
    assert report(c) == before_report


def test_campaign_edit_keeps_existing_write_rbac_and_order_workspace_guard(campaign_editor):
    c = campaign_editor
    baseline = stored(c)
    c.actor.workspaces[0].role.name = "ANALYST"
    assert c.client.put(f"/api/v1/orders/{c.order}", headers=headers(c), json={"campaign_id": str(c.active)}).status_code == 403
    assert stored(c) == baseline
    c.actor.workspaces[0].role.name = "MANAGER"
    assert c.client.put(f"/api/v1/orders/{c.foreign_order}", headers=headers(c), json={"campaign_id": str(c.active)}).status_code == 404
    assert stored(c) == baseline
    with Session(c.engine) as db:
        assert db.get(Order, c.foreign_order).campaign_id is None


@pytest.mark.parametrize("status", ["NEW", "SHIPPED", "COMPLETED", "CANCELLED"])
def test_service_campaign_only_metadata_does_not_replace_items_or_move_stock(campaign_editor, status):
    c = campaign_editor
    with Session(c.engine) as db:
        db.execute(Order.__table__.update().where(Order.id == c.order).values(
            status=status, net_profit=0 if status == "CANCELLED" else 69))
        db.commit()
    baseline = stored(c)
    with Session(c.engine, autoflush=False) as db:
        result = OrderService(db).update(c.workspace, c.order, OrderUpdate(campaign_id=c.archived), c.actor.id)
        assert result is not None and result.campaign_id == c.archived
    snapshot = stored(c)
    assert snapshot["campaign"] == c.archived
    assert {key: value for key, value in snapshot.items() if key not in {"campaign", "audit"}} == {
        key: value for key, value in baseline.items() if key not in {"campaign", "audit"}
    }
