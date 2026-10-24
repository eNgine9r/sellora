"""Disposable PostgreSQL integration canary. Opt-in only on empty temporary DB.

Requires already-applied Alembic head 046. Do not point at a real workspace.
"""
from datetime import UTC, datetime
import os
from uuid import uuid4

from sqlalchemy import select, text

from app.database.session import SessionLocal
from app.models.ai_direct import DirectConversation, DirectMessage
from app.models.customer import Customer
from app.models.direct_order_shipment_link import DirectOrderShipmentLink
from app.models.order import Order
from app.models.shipment import Shipment
from app.models.user import User
from app.models.workspace import Workspace
from app.services.direct_ttn_evidence_service import DirectTtnEvidenceService

assert os.environ.get("SELLORA_TTN_DISPOSABLE_CANARY") == "YES", "Must explicitly opt in to disposable test"

with SessionLocal() as db:
    assert db.scalar(text("SELECT version_num FROM alembic_version")) == "202610240046"
    assert db.scalar(text("SELECT count(*) FROM workspaces")) == 0, "NOT DISPOSABLE: workspaces exist"
    user = User(email="canary@example.invalid", password_hash="not-a-real-password",
                first_name="Canary", last_name="Tester")
    wa = Workspace(name="TTN CANARY A", slug="ttn-canary-a")
    wb = Workspace(name="TTN CANARY B", slug="ttn-canary-b")
    db.add_all([user, wa, wb]); db.flush()
    ca = Customer(workspace_id=wa.id, name="synthetic buyer")
    cb = Customer(workspace_id=wb.id, name="tenant 2 synthetic buyer")
    db.add_all([ca, cb]); db.flush()
    d1 = DirectConversation(workspace_id=wa.id, channel="INSTAGRAM", linked_customer_id=ca.id)
    d2 = DirectConversation(workspace_id=wb.id, channel="INSTAGRAM", linked_customer_id=cb.id)
    d3 = DirectConversation(workspace_id=wa.id, channel="INSTAGRAM", linked_customer_id=ca.id)
    db.add_all([d1,d2,d3]); db.flush()
    now=datetime.now(UTC)
    ttn_a="20451234567890"; ttn_b="20459876543210"; ttn_unknown="20450000123456"
    db.add_all([
        DirectMessage(workspace_id=wa.id, conversation_id=d1.id, direction="OUTBOUND",sender_type="MANAGER",text="Нова пошта ТТН "+ttn_a,received_at=now),
        DirectMessage(workspace_id=wa.id, conversation_id=d1.id, direction="OUTBOUND",sender_type="MANAGER",text="Ось ще одна ТТН "+ttn_b,received_at=now),
        DirectMessage(workspace_id=wa.id, conversation_id=d1.id, direction="OUTBOUND",sender_type="MANAGER",text="Пошта: ТТН "+ttn_unknown,received_at=now),
        DirectMessage(workspace_id=wa.id, conversation_id=d1.id, direction="OUTBOUND",sender_type="MANAGER",text="Повтор "+ttn_a,received_at=now),
        DirectMessage(workspace_id=wb.id, conversation_id=d2.id, direction="OUTBOUND",sender_type="MANAGER",text="ТТН "+ttn_a,received_at=now),
        DirectMessage(workspace_id=wa.id, conversation_id=d3.id, direction="OUTBOUND",sender_type="MANAGER",text="ТТН "+ttn_b,received_at=now),
    ])
    o1 = Order(workspace_id=wa.id,order_number="CANARY1",customer_id=ca.id)
    o2 = Order(workspace_id=wa.id,order_number="CANARY2",customer_id=ca.id)
    db.add_all([o1,o2]); db.flush()
    s1=Shipment(workspace_id=wa.id,order_id=o1.id,customer_id=ca.id,tracking_number=ttn_a,carrier="NOVA_POSHTA")
    s2=Shipment(workspace_id=wa.id,order_id=o2.id,customer_id=ca.id,tracking_number=ttn_b,carrier="NOVA_POSHTA")
    db.add_all([s1,s2]); db.commit()
    service=DirectTtnEvidenceService(db)
    preview=service.preview(wa.id,d1.id)
    assert preview is not None
    assert len(preview["verified_orders"])==2, preview
    assert len(preview["needs_review"])==1,preview
    assert preview["needs_review"][0]["reason"]=="SHIPMENT_NOT_IN_CRM"
    assert preview["has_multiple_orders"] is True
    assert service.preview(wb.id,d1.id) is None
    assert len(service.preview(wb.id,d2.id)["verified_orders"])==0
    assert service.preview(wb.id,d2.id)["needs_review"][0]["reason"]=="SHIPMENT_NOT_IN_CRM"
    ids={o1.id,o2.id}
    actual=service.confirm(wa.id,d1.id,ids,user.id)
    assert actual["created_links"]==2 and actual["primary_order_linked"] is False
    db.commit()
    again=service.confirm(wa.id,d1.id,ids,user.id)
    assert again["created_links"]==0 and again["existing_links"]==2
    db.commit()
    assert db.scalar(select(DirectConversation.linked_order_id).where(DirectConversation.id==d1.id)) is None
    assert db.scalar(select(DirectOrderShipmentLink).where(DirectOrderShipmentLink.conversation_id==d1.id)) is not None
    single=service.preview(wa.id,d3.id)
    assert len(single["verified_orders"])==1
    s=service.confirm(wa.id,d3.id,{o2.id},user.id)
    assert s["primary_order_linked"] and s["created_links"]==1
    db.commit()
    assert db.scalar(select(DirectConversation.linked_order_id).where(DirectConversation.id==d3.id))==o2.id
    assert db.scalar(text("SELECT count(*) FROM direct_order_shipment_links"))==3
    assert db.scalar(text("SELECT count(*) FROM audit_logs WHERE entity_type = 'DIRECT_ORDER_SHIPMENT_LINK'"))==3
    assert db.scalar(text("SELECT count(*) FROM orders"))==2
    assert db.scalar(text("SELECT count(*) FROM shipments"))==2
    print("ISOLATED_PG16_SCHEMA046_EXACT_TTN_MULTI_ORDER_IDEMPOTENCY_TENANT_AUDIT_PASS")
