"""Order-safe NP tracking, worker isolation and status-code regressions."""
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.integrations.nova_poshta_client import NovaPoshtaClient, NovaPoshtaClientError, NovaPoshtaTrackingResult
from app.models.order import OrderStatus
from app.models.shipment import Shipment, ShipmentCarrier, ShipmentStatus
from app.services.nova_poshta_tracking import normalize_tracking_status, should_apply_tracking_status
from app.services.nova_poshta_tracking_worker import pending_tracking_ids, enabled, BATCH_LIMIT
from app.services.nova_poshta_service import NovaPoshtaShipmentService


@pytest.mark.parametrize(
    ("code","state"),
    [
        ("1", ShipmentStatus.CREATED), ("4", ShipmentStatus.IN_TRANSIT),
        ("5", ShipmentStatus.IN_TRANSIT), ("6", ShipmentStatus.IN_TRANSIT),
        ("7", ShipmentStatus.ARRIVED), ("8", ShipmentStatus.ARRIVED),
        ("9", ShipmentStatus.DELIVERED), ("10", ShipmentStatus.DELIVERED),
        ("11", ShipmentStatus.DELIVERED), ("101", ShipmentStatus.IN_TRANSIT),
        ("103", None), ("102", None), ("106", None),
        ("104", None), ("105", None), ("2", None), ("3", None),
        ("not-a-code", None),
    ],
)
def test_tracking_status_numeric_codes(code, state):
    assert normalize_tracking_status(code, "Відправлення отримано") == state


def test_no_status_regressions_and_unknown_review():
    assert not should_apply_tracking_status(ShipmentStatus.DELIVERED, ShipmentStatus.CREATED)
    assert not should_apply_tracking_status(ShipmentStatus.IN_TRANSIT, ShipmentStatus.CREATED)
    assert not should_apply_tracking_status(ShipmentStatus.ARRIVED, ShipmentStatus.IN_TRANSIT)
    assert not should_apply_tracking_status(ShipmentStatus.RETURNED, ShipmentStatus.DELIVERED)
    assert not should_apply_tracking_status(ShipmentStatus.CANCELLED, ShipmentStatus.DELIVERED)
    assert not should_apply_tracking_status(ShipmentStatus.ARRIVED, None)
    assert should_apply_tracking_status(ShipmentStatus.CREATED, ShipmentStatus.IN_TRANSIT)
    assert should_apply_tracking_status(ShipmentStatus.IN_TRANSIT, ShipmentStatus.DELIVERED)


def test_client_parses_status_and_rejects_wrong_ttn():
    client = NovaPoshtaClient("synthetic-key")
    client._call = lambda *a, **k: {"data": [{
        "Number": "20400000000001", "Status": "Очікуємо посилку", "StatusCode": "1"
    }]}
    value = client.get_document_tracking("20400000000001")
    assert value == NovaPoshtaTrackingResult(status="Очікуємо посилку",code="1")
    assert client.get_document_status("20400000000001") == "Очікуємо посилку"
    with pytest.raises(NovaPoshtaClientError) as exc:
        client.get_document_tracking("20400000000002")
    assert exc.value.code == "NOVA_POSHTA_TRACKING_NUMBER_MISMATCH"


class FakeDb:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


def _service(code, text, current=ShipmentStatus.CREATED, order_status="NEW"):
    workspace_id, order_id = uuid4(), uuid4()
    sh = Shipment(
        id=uuid4(), workspace_id=workspace_id, order_id=order_id,
        carrier=ShipmentCarrier.NOVA_POSHTA.value, status=current.value,
        tracking_number="20400000000001", nova_poshta_document_number="20400000000001",
    )
    order = SimpleNamespace(id=order_id, status=order_status, payment_status="COD")
    client = SimpleNamespace(get_document_tracking=lambda n: NovaPoshtaTrackingResult(status=text,code=code))
    db = FakeDb()
    audit = []

    service = NovaPoshtaShipmentService.__new__(NovaPoshtaShipmentService)
    service.db = db
    service.settings = SimpleNamespace(_require_connection=lambda w:(None,"synthetic-key"),client_factory=lambda key:client)
    service.shipments = SimpleNamespace(get_for_update=lambda w,s:sh if w==workspace_id and s==sh.id else None)
    service.audit_logs = SimpleNamespace(create=lambda **kw:audit.append(kw))
    return service,sh,order,audit,db


def test_sync_created_preserves_payment_even_with_delivered_code():
    service,sh,order,audit,db = _service("9","Відправлення отримано")
    result = service.sync_status(sh.workspace_id,sh.id,None)
    assert result.success
    assert result.normalized_status == "DELIVERED"
    assert sh.delivered_at is not None and sh.shipped_at is not None
    assert sh.nova_poshta_synced_at is not None
    assert order.payment_status == "COD"
    assert any(x["action"]=="NOVA_POSHTA_STATUS_SYNCED" and x["new_value"]["payment_unchanged"] for x in audit)
    assert db.commits==1


def test_sync_rejects_regressive_provider_code():
    service,sh,order,audit,db = _service("1","Відправник створив",current=ShipmentStatus.IN_TRANSIT)
    result=service.sync_status(sh.workspace_id,sh.id,None)
    assert result.success
    assert sh.status=="IN_TRANSIT"
    assert result.manual_review_required is False
    assert audit[-1]["new_value"]["changed"] is False


def test_sync_refusal_does_not_cause_auto_return():
    service,sh,order,audit,db = _service("103","Відмова отримувача",current=ShipmentStatus.ARRIVED)
    result=service.sync_status(sh.workspace_id,sh.id,None)
    assert result.success and result.manual_review_required
    assert sh.status=="ARRIVED"
    assert order.payment_status=="COD"


def test_sync_provider_key_is_scoped_and_requires_correct_workspace():
    service,sh,order,audit,db = _service("9","Отримано")
    with pytest.raises(ValueError,match="Shipment not found"):
        service.sync_status(uuid4(),sh.id,None)
    assert db.commits==0


def test_order_transition_uses_allowed_states_and_never_changes_payment(monkeypatch):
    import app.services.nova_poshta_service as module

    fake_order=SimpleNamespace(id=uuid4(),status=OrderStatus.NEW.value,payment_status="COD")
    transitions=[]
    class DummyOrders:
        def __init__(self, db):
            pass
        def get(self, workspace_id, order_id):
            assert fake_order.id==order_id
            return fake_order
        def change_status(self, workspace_id, order_id, payload, user_id, commit=False):
            assert not commit
            transitions.append(payload.status.value)
            fake_order.status=payload.status.value

    monkeypatch.setattr(module, "OrderService", DummyOrders)
    # A real (unbound) SQLAlchemy Session is sufficient to exercise the branch.
    service=NovaPoshtaShipmentService.__new__(NovaPoshtaShipmentService)
    service.db=Session()
    try:
        service._update_order_for_tracking(uuid4(),SimpleNamespace(order_id=fake_order.id),ShipmentStatus.DELIVERED,None)
    finally:
        service.db.close()
    assert transitions==["CONFIRMED","SHIPPED","DELIVERED"]
    assert fake_order.payment_status=="COD"


def test_worker_sql_scopes_shipments_to_connected_workspaces_and_bounded_batch():
    class RecordingDb:
        def __init__(self):
            self.stmt=None
        def execute(self, stmt):
            self.stmt=stmt
            return SimpleNamespace(all=lambda:[])
    db=RecordingDb()
    assert pending_tracking_ids(db,now=datetime.now(UTC),limit=1000)==[]
    sql=str(db.stmt)
    assert "shipments.workspace_id" in sql
    assert "integration_connections.workspace_id" in sql
    assert "workspaces.is_active" in sql
    assert "shipments.deleted_at IS NULL" in sql
    # An older shipment draft with a recently created TTN must remain eligible.
    assert "shipments.updated_at" in sql
    assert "shipments.created_at >=" not in sql
    assert "integration_connections.deleted_at IS NULL" in sql
    assert BATCH_LIMIT==10


def test_worker_is_opt_in(monkeypatch):
    monkeypatch.delenv("SELLORA_NP_TRACKING_SYNC_ENABLED",raising=False)
    assert not enabled()
    monkeypatch.setenv("SELLORA_NP_TRACKING_SYNC_ENABLED","true")
    assert enabled()
