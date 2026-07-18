from app.models.order_fulfillment import ACTIVE_FULFILLMENT_STATES, OrderFulfillmentState


def test_canonical_fulfillment_state_machine_contains_active_release_states() -> None:
    assert OrderFulfillmentState.RECONCILIATION_REQUIRED.value in ACTIVE_FULFILLMENT_STATES
    assert OrderFulfillmentState.COMPLETED.value not in ACTIVE_FULFILLMENT_STATES
    assert OrderFulfillmentState.CANCELLED.value not in ACTIVE_FULFILLMENT_STATES
