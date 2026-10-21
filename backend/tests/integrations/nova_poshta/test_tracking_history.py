from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.services.shipment_service import ShipmentService


def _event(action, created_at, fields):
    return SimpleNamespace(action=action, created_at=created_at, new_value=fields)


def test_tracking_history_ignores_provider_poll_duplicates_and_never_returns_pii():
    workspace, shipment = uuid4(), uuid4()
    now = datetime.now(UTC)
    # database returns most recent first
    rows = [
        _event("NOVA_POSHTA_STATUS_SYNCED", now, {
            "changed": True, "normalized_status": "ARRIVED",
            "previous_normalized_status": "IN_TRANSIT", "provider_status_code": "7",
            "customer_phone": "SENSITIVE",
        }),
        _event("NOVA_POSHTA_STATUS_SYNCED", now - timedelta(minutes=15), {
            "changed": False, "normalized_status": "IN_TRANSIT",
            "previous_normalized_status": "IN_TRANSIT",
        }),
        _event("NOVA_POSHTA_STATUS_SYNCED", now - timedelta(hours=1), {
            "changed": True, "normalized_status": "IN_TRANSIT",
            "previous_normalized_status": "CREATED", "provider_status_code": "5",
        }),
        _event("NOVA_POSHTA_TTN_CREATED", now-timedelta(hours=5), {"provider":"NOVA_POSHTA"}),
    ]
    class FakeDb:
        def scalars(self, query):
            sql=str(query)
            assert "audit_logs.workspace_id" in sql
            assert "audit_logs.entity_id" in sql
            assert "audit_logs.entity_type" in sql
            return SimpleNamespace(all=lambda: rows)
    svc=ShipmentService.__new__(ShipmentService)
    svc.db=FakeDb()
    svc.shipments=SimpleNamespace(get=lambda w,s: SimpleNamespace(id=s) if (w,s)==(workspace,shipment) else None)
    result=svc.tracking_history(workspace,shipment)
    assert [e.status for e in result]==["ARRIVED","IN_TRANSIT","CREATED"]
    assert result[0].provider_status_code=="7"
    assert "SENSITIVE" not in str([e.model_dump() for e in result])
    assert svc.tracking_history(uuid4(),shipment) is None


def test_tracking_history_rejects_malformed_or_unknown_statuses():
    now=datetime.now(UTC)
    rows=[
        _event("NOVA_POSHTA_STATUS_SYNCED", now, {"changed":True,"normalized_status":"UNKNOWN","provider_status_code":"bad"}),
        _event("NOVA_POSHTA_STATUS_SYNCED", now, {"changed":True,"normalized_status":"RETURNED","provider_status_code":"9"*150}),
    ]
    svc=ShipmentService.__new__(ShipmentService)
    svc.db=SimpleNamespace(scalars=lambda q:SimpleNamespace(all=lambda:rows))
    svc.shipments=SimpleNamespace(get=lambda w,s:SimpleNamespace(id=s))
    events=svc.tracking_history(uuid4(),uuid4())
    assert len(events)==1 and events[0].status=="RETURNED"
    assert events[0].provider_status_code is None
