"""Regression: provider-confirmed 4 moving, 1 arrived; no double counts/tenant leaks."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.integrations.nova_poshta_client import NovaPoshtaTrackingResult
from app.services.nova_poshta_external_inbox_service import NovaPoshtaExternalInboxService
from app.services.nova_poshta_external_status import infer_external_shipment_status
from app.services.shipment_live_summary import compute_counts


NOW = datetime(2026, 11, 12, 8, 30, tzinfo=UTC)


def crm(status, tracking, *, carrier="NOVA_POSHTA"):
    return SimpleNamespace(
        id=uuid4(), status=status, carrier=carrier,
        tracking_number=tracking, nova_poshta_document_number=None,
    )


def external(number, *, normalized=None, raw=None, checked=NOW):
    return SimpleNamespace(
        tracking_number=number,
        provider_status=raw,
        provider_normalized_status=normalized,
        provider_tracking_checked_at=checked,
    )


def test_realtime_provider_snapshot_4_transit_1_arrived_and_historical_crm():
    docs = [external(str(i), normalized="IN_TRANSIT") for i in range(4)]
    docs += [external("arrived", normalized="ARRIVED")]
    docs += [external("delivered", raw="Відправлення отримано", checked=None)]
    stored = [crm("CREATED", "one-old-order"), crm("DELIVERED", "older-complete")]
    result = compute_counts(stored, docs, now=NOW)
    assert result.in_transit_count == 4
    assert result.arrived_count == 1
    assert result.crm_total_count == 2
    assert result.crm_ready_count == 1
    assert result.crm_delivered_count == 1
    assert result.provider_pending_count == 0


def test_linked_waybill_is_counted_once_and_terminal_crm_does_not_regress():
    stored = [crm("IN_TRANSIT", "same"), crm("DELIVERED", "finished")]
    docs = [
        external("same", normalized="IN_TRANSIT"),
        external("finished", raw="Відправлення прямує до м. Київ", checked=None),
    ]
    result = compute_counts(stored, docs, now=NOW)
    assert result.in_transit_count == 1
    assert result.arrived_count == 0
    assert result.crm_delivered_count == 1
    assert result.provider_pending_count == 1


def test_unrecognized_provider_text_is_not_in_transit():
    assert infer_external_shipment_status("Невідомий статус") is None
    assert infer_external_shipment_status("Відмова від отримання") is None
    assert infer_external_shipment_status("Відправлення у м. Київ. Очікуйте повідомлення про прибуття").value == "IN_TRANSIT"
    assert infer_external_shipment_status("Прибув до поштомату").value == "ARRIVED"


def test_verified_tracking_advances_legacy_external_waybills_no_order_writes():
    docs = [external(str(i), raw="Відправлення прямує до м. Київ", normalized=None, checked=None) for i in range(5)]
    class FakeClient:
        def get_document_tracking(self, number):
            code = "7" if number == "4" else "4"
            return NovaPoshtaTrackingResult(status="Прибув до відділення" if code == "7" else "Відправлення прямує", code=code)
    service = NovaPoshtaExternalInboxService.__new__(NovaPoshtaExternalInboxService)
    service.settings = SimpleNamespace(_require_connection=lambda workspace_id: (None, "test-key"))
    service.repo = SimpleNamespace(tracking_candidates=lambda workspace_id, now, limit: docs)
    service.client_factory = lambda key: FakeClient()
    service.db = MagicMock()
    stats = service.refresh_tracking(uuid4())
    assert stats == {"eligible": 5, "checked": 5, "changed": 5, "unverified": 0, "failed": 0}
    result = compute_counts([], docs, now=datetime.now(UTC))
    assert result.in_transit_count == 4
    assert result.arrived_count == 1
    assert result.provider_pending_count == 0
    assert service.db.commit.call_count == 5
