from app.services.order_fulfillment_service import OrderFulfillmentService


def test_reconciliation_uses_provider_reconcile_method_name() -> None:
    assert "reconcile_ttn" in OrderFulfillmentService.reconcile_fulfillment.__code__.co_names
