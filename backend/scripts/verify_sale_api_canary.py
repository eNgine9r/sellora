"""Opt-in API sale canary for an empty, disposable PostgreSQL database only.

Run after Alembic head. Never import production env or point at a real database.
No provider document, outbound message, campaign or paid AI call is permitted.
"""
import json
import os
import secrets
from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.auth.password import hash_password
from app.database.session import SessionLocal, engine
from app.main import app
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_user import WorkspaceUser
from app.models.role import Role
from app.models.meta_instagram import InstagramConnection
from app.models.ai_direct import DirectConversation, DirectMessage
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.inventory import Inventory

assert os.getenv("SELLORA_SALE_DISPOSABLE_CANARY") == "YES"
assert (engine.url.host == "sellora-resilience-pg17-20261025" and engine.url.database == "sellora_qa") or (engine.url.host in {"localhost", "127.0.0.1"} and engine.url.database == "sellora_sale_canary_isolated"), "Unexpected disposable database target"
assert os.getenv("STAGING_NOVA_POSHTA_ALLOW_WRITES") == "false"
assert os.getenv("META_INSTAGRAM_WEBHOOK_WORKER_ENABLED") == "false"
password = secrets.token_urlsafe(24)
with SessionLocal() as db:
    assert db.scalar(text("SELECT count(*) FROM workspaces")) == 0, "Database is not empty"
    assert db.scalar(text("SELECT version_num FROM alembic_version")) == "202610270049"
    ws = Workspace(name="Isolated sale QA", slug="isolated-sale-qa")
    other = Workspace(name="Other tenant QA", slug="other-sale-qa")
    users = [User(email=f"sale-{role.lower()}@example.com", password_hash=hash_password(password),
                  first_name="Synthetic", last_name=role) for role in ("MANAGER", "ANALYST")]
    db.add_all([ws, other, *users]); db.flush()
    for user, role in zip(users, ("MANAGER", "ANALYST")):
        role_id = db.scalar(select(Role.id).where(Role.name == role))
        if role_id is None:
            new_role = Role(name=role); db.add(new_role); db.flush(); role_id=new_role.id
        db.add(WorkspaceUser(workspace_id=ws.id, user_id=user.id, role_id=role_id))
    connection = InstagramConnection(workspace_id=ws.id, instagram_account_id="synthetic-sale-account", status="CONNECTED")
    db.add(connection); db.flush()
    conversation = DirectConversation(workspace_id=ws.id, channel="INSTAGRAM",
        instagram_connection_id=connection.id, participant_scoped_id="synthetic-sale-buyer",
        participant_username="synthetic_sale_buyer", participant_display_name="Synthetic buyer")
    product = Product(workspace_id=ws.id, name="QA product", is_active=True)
    db.add_all([conversation, product]); db.flush()
    variant = ProductVariant(workspace_id=ws.id, product_id=product.id, sku="SALE-QA-1", price=Decimal("500"))
    db.add(variant); db.flush()
    inventory = Inventory(workspace_id=ws.id, product_variant_id=variant.id, stock_quantity=5, reserved_quantity=0)
    db.add_all([inventory, DirectMessage(workspace_id=ws.id, conversation_id=conversation.id,
        direction="INBOUND", sender_type="CUSTOMER", provider="INSTAGRAM",
        text="Хочу замовити один товар", received_at=datetime.now(UTC))])
    db.commit()
    ws_id, other_id, conv_id, variant_id = ws.id, other.id, conversation.id, variant.id

with TestClient(app, base_url="http://localhost:3000") as client:
    def login(role):
        r = client.post("/api/v1/auth/session/login", headers={"Origin":"http://localhost:3000"},
                        json={"email":f"sale-{role.lower()}@example.com","password":password})
        assert r.status_code == 200, ("login", r.status_code)
        return {"Authorization":"Bearer "+r.json()["access_token"], "X-Workspace-ID":str(ws_id)}
    manager = login("MANAGER")
    analyst = login("ANALYST")
    def request(method, path, *, status=200, headers=None, **kwargs):
        r = client.request(method, "/api/v1"+path, headers=headers or manager, **kwargs)
        assert r.status_code == status, (path, r.status_code, r.text[:300])
        return r.json() if r.content else None
    lead_path = f"/direct/conversations/{conv_id}/lead/ensure"
    request("POST", lead_path, headers=analyst, status=403)
    request("POST", lead_path, headers=manager | {"X-Workspace-ID":str(other_id)}, status=403)
    first = request("POST", lead_path)
    again = request("POST", lead_path)
    assert first["linked_lead_id"] == again["linked_lead_id"]
    customer = request("POST", f"/direct/conversations/{conv_id}/customer-automation/ensure")["customer"]
    repeated_customer = request("POST", f"/direct/conversations/{conv_id}/customer-automation/ensure")["customer"]
    assert customer["id"] == repeated_customer["id"]
    payload = {
        "idempotency_key":"isolated-sale-20261025",
        "customer_id":customer["id"], "source_direct_conversation_id":str(conv_id),
        "recipient_name":"Synthetic buyer", "recipient_phone":"+380671234567",
        "nova_poshta_city_ref":"synthetic-city", "city":"Київ",
        "nova_poshta_warehouse_ref":"synthetic-warehouse", "warehouse":"Тестове відділення",
        "items":[{"product_variant_id":str(variant_id),"quantity":1,"unit_price":"500","unit_cost":"120"}],
        "payment_status":"COD", "create_ttn":False,
    }
    sale = request("POST", "/order-fulfillments", status=201, json=payload)
    replay = request("POST", "/order-fulfillments", status=201, json=payload)
    order_id = sale["order"]["id"]
    assert replay["order"]["id"] == order_id and replay["idempotent_replay"]
    assert not sale["tracking_number"]
    # Source linkage is part of the committed workflow, not a second UI write.
    with SessionLocal() as db:
        conv = db.get(DirectConversation, conv_id)
        assert str(conv.linked_order_id) == order_id, "SOURCE_DIRECT_ORDER_LINK_MISSING"
        assert db.scalar(text("SELECT status FROM leads")) == "CONVERTED"
        assert db.scalar(text("SELECT count(*) FROM audit_logs WHERE action='DIRECT_ORDER_LINK'")) == 1
        assert db.scalar(text("SELECT count(*) FROM leads")) == 1
        assert db.scalar(text("SELECT count(*) FROM customers")) == 1
        assert db.scalar(text("SELECT count(*) FROM orders")) == 1
        assert db.scalar(text("SELECT count(*) FROM shipments")) == 1
        stock = db.scalar(select(Inventory).where(Inventory.workspace_id==ws_id))
        assert (stock.stock_quantity, stock.reserved_quantity) == (5,1)
    request("POST", f"/orders/{order_id}/status", json={"status":"CONFIRMED"})
    prepare = request("POST", f"/orders/{order_id}/fulfillment/prepare", json={
        "customer_id":customer["id"],"recipient":{"name":"Synthetic buyer","phone":"+380671234567"},
        "delivery":{"city_ref":"synthetic-city","city_description":"Київ","warehouse_ref":"synthetic-warehouse","warehouse_description":"Тестове відділення"},
        "payment":{"mode":"COD","cod_amount":"500"},
    })
    assert prepare["ready"], prepare["blockers"]
    assert prepare["finance_preview"]["recognized_revenue"] == "0"
    request("POST", "/order-fulfillments", headers=analyst, status=403, json=payload)
    request("GET", f"/orders/{order_id}", headers=manager | {"X-Workspace-ID":str(other_id)}, status=403)
    with SessionLocal() as db:
        assert db.scalar(text("SELECT count(*) FROM direct_messages WHERE direction='OUTBOUND'")) == 0
        assert db.scalar(text("SELECT count(*) FROM nova_poshta_operations")) == 0
        assert db.scalar(text("SELECT count(*) FROM shipments WHERE tracking_number IS NOT NULL")) == 0
    # Exercise actual persistence and reporting for unknown versus confirmed
    # zero, including a reload through the public API. No provider writes.
    base = dict(payload)
    base.pop("source_direct_conversation_id")
    base["idempotency_key"] = "isolated-unknown-cost"
    base["items"] = [dict(product_variant_id=str(variant_id), quantity=1, unit_price="500", unit_cost="0", cost_confirmed=False)]
    unknown = request("POST", "/order-fulfillments", status=201, json=base)["order"]
    assert unknown["product_cost"] is None and unknown["net_profit"] is None
    assert request("GET", f"/orders/{unknown['id']}")["net_profit"] is None
    base["idempotency_key"] = "isolated-confirmed-zero"
    base["items"][0]["cost_confirmed"] = True
    confirmed_zero = request("POST", "/order-fulfillments", status=201, json=base)["order"]
    assert Decimal(confirmed_zero["product_cost"]) == 0
    assert Decimal(confirmed_zero["net_profit"]) == 500
    finance = request("GET", "/finance/summary", headers=analyst)
    assert finance["cogs"] is None and finance["net_profit"] is None
    assert request("GET", "/analytics/profit-summary", headers=analyst)["total_net_profit"] is None
    assert request("GET", "/analytics/sales-report", headers=analyst)["net_profit"] is None
    assert request("GET", "/analytics/top-products", headers=analyst)[0]["net_profit"] is None
    assert request("GET", "/orders/dashboard", headers=analyst)["profit_today"] is None
    with SessionLocal() as db:
        assert db.scalar(text("SELECT count(*) FROM order_items WHERE cost_confirmed IS FALSE")) == 1
        assert db.scalar(text("SELECT count(*) FROM order_items WHERE cost_confirmed IS TRUE")) == 1
        assert db.scalar(text("SELECT count(*) FROM nova_poshta_operations")) == 0
        assert db.scalar(text("SELECT count(*) FROM direct_messages WHERE direction='OUTBOUND'")) == 0
    corrected = request("PUT", f"/orders/{unknown['id']}", json={"items":[
        dict(product_variant_id=str(variant_id), quantity=1, unit_price="500", unit_cost="200", cost_confirmed=True)
    ]})
    assert Decimal(corrected["product_cost"]) == 200 and Decimal(corrected["net_profit"]) == 300
    finance = request("GET", "/finance/summary", headers=analyst)
    assert Decimal(finance["cogs"]) == 320 and Decimal(finance["net_profit"]) == 1180
    assert Decimal(request("GET", "/analytics/profit-summary", headers=analyst)["total_net_profit"]) == 1180
    print("COST_COMPLETENESS_API_CANARY=PASS")
    print(json.dumps({"sale_api_canary":"PASS","lead":1,"customer":1,"order":3,"shipment_draft":3,
        "reserved_quantity":3,"stock_quantity":5,"provider_writes":0,"outbound_messages":0,
        "replay_dedup":"PASS","analyst_and_tenant_denial":"PASS","prepare":"READY"}))
