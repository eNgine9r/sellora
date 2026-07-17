"""Shared test fixtures for legacy scenarios after Sprint 8D lifecycle hardening.

The production service rejects direct NEW -> SHIPPED/COMPLETED transitions. A small
set of older unit tests validates downstream stock/archive/customer side effects and
predates that state machine. For those exact tests only, this fixture prepares the
order through the current approved intermediate statuses before the original
assertions execute. No production service behavior is patched.
"""

from __future__ import annotations

import pytest

from app.models.order import OrderStatus
from app.schemas.order import OrderStatusUpdate


_CONFIRM_BEFORE_TEST = {
    "test_shipping_order_decreases_stock_and_reserved_quantities",
    "test_returning_order_restores_inventory_after_shipping",
    "test_archive_shipped_order_is_rejected",
    "test_shipped_order_rejects_item_edit_but_safe_fields_update",
}

_DELIVER_BEFORE_TEST = {
    "test_completed_order_updates_customer_metrics",
}


@pytest.fixture(autouse=True)
def align_legacy_order_tests_with_current_status_path(request, monkeypatch):
    if request.module.__name__.split(".")[-1] != "test_orders":
        return
    if request.node.name not in _CONFIRM_BEFORE_TEST | _DELIVER_BEFORE_TEST:
        return

    original_create_order = request.module._create_order

    def create_order_through_current_path(service, inventory, customer):
        order = original_create_order(service, inventory, customer)
        service.change_status(
            inventory.workspace_id,
            order.id,
            OrderStatusUpdate(status=OrderStatus.CONFIRMED),
            actor_user_id=None,
        )
        if request.node.name in _DELIVER_BEFORE_TEST:
            service.change_status(
                inventory.workspace_id,
                order.id,
                OrderStatusUpdate(status=OrderStatus.SHIPPED),
                actor_user_id=None,
            )
            service.change_status(
                inventory.workspace_id,
                order.id,
                OrderStatusUpdate(status=OrderStatus.DELIVERED),
                actor_user_id=None,
            )
        return order

    monkeypatch.setattr(request.module, "_create_order", create_order_through_current_path)
