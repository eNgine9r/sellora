"""Compatibility helpers for lightweight in-memory service doubles.

Production repositories expose get_for_update() and real SQLAlchemy sessions expose
flush(). The legacy unit doubles predate those methods, so the test harness supplies
only the missing protocol methods. Runtime concurrency remains covered separately
against PostgreSQL staging.
"""


def pytest_configure() -> None:
    from tests import test_orders, test_shipments

    if not hasattr(test_orders.FakeOrders, "get_for_update"):
        test_orders.FakeOrders.get_for_update = test_orders.FakeOrders.get
    if not hasattr(test_orders.FakeDb, "flush"):
        test_orders.FakeDb.flush = lambda self: None

    if not hasattr(test_shipments.FakeShipmentRepo, "get_for_update"):
        test_shipments.FakeShipmentRepo.get_for_update = test_shipments.FakeShipmentRepo.get
    if not hasattr(test_shipments.FakeOrderRepo, "get_for_update"):
        test_shipments.FakeOrderRepo.get_for_update = test_shipments.FakeOrderRepo.get
    if not hasattr(test_shipments.FakeDb, "flush"):
        test_shipments.FakeDb.flush = lambda self: None

    original_change_status = test_shipments.FakeOrderService.change_status
    if not getattr(original_change_status, "_accepts_commit", False):
        def change_status(self, workspace_id, order_id, payload, actor_user_id, commit=True):
            return original_change_status(self, workspace_id, order_id, payload, actor_user_id)

        change_status._accepts_commit = True
        test_shipments.FakeOrderService.change_status = change_status
