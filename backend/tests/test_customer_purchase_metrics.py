"""Customer metrics must reflect linked workspace orders rather than stale counters."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.models.customer import Customer
from app.models.order import OrderStatus, PaymentStatus
from app.services.customer_service import CustomerService


def _customer(workspace_id, customer_id):
    created = datetime.now(UTC) - timedelta(days=30)
    return Customer(
        id=customer_id, workspace_id=workspace_id,
        name="Customer", phone=None, instagram_username=None,
        city=None, region=None, total_orders=0, total_spent=Decimal("0"),
        created_at=created, updated_at=created,
    )


def _svc(customers, rows):
    service = CustomerService.__new__(CustomerService)
    service.customers = SimpleNamespace(list_for_workspace=lambda ws, search: customers, get=lambda ws, cid: next((c for c in customers if c.id == cid and c.workspace_id == ws), None))
    service.db = MagicMock()
    service.db.execute.return_value.all.return_value = rows
    return service


def test_live_metrics_count_orders_but_spending_only_after_payment():
    wid, cid = uuid4(), uuid4()
    now = datetime.now(UTC)
    rows = [
        (cid, "NP-CURRENT", OrderStatus.DELIVERED.value, PaymentStatus.PENDING.value, Decimal("0"), True, now, uuid4()),
        (cid, "ORD-PAID", OrderStatus.COMPLETED.value, PaymentStatus.PAID.value, Decimal("749"), False, now - timedelta(days=2), uuid4()),
        (cid, "ORD-RETURNED", OrderStatus.RETURNED.value, PaymentStatus.PAID.value, Decimal("600"), False, now - timedelta(days=4), uuid4()),
    ]
    service = _svc([_customer(wid, cid)], rows)
    result = service.list(wid)
    assert len(result) == 1
    item = result[0]
    assert item.total_orders == 3
    assert item.paid_orders == 1
    assert item.total_spent == Decimal("749")
    assert item.unpriced_orders == 1
    assert item.last_order_number == "NP-CURRENT"
    assert item.last_order_payment_status == PaymentStatus.PENDING.value
    assert item.last_order_at == now
    # Never mutate the persisted customer fields as part of a read.
    assert service.customers.list_for_workspace(wid, None)[0].total_orders == 0
    assert "orders.workspace_id" in str(service.db.execute.call_args.args[0])


def test_no_linked_orders_have_truthful_empty_history():
    wid, cid = uuid4(), uuid4()
    service = _svc([_customer(wid, cid)], [])
    item = service.list(wid)[0]
    assert item.total_orders == 0
    assert item.paid_orders == 0
    assert item.total_spent == 0
    assert item.last_order_at is None


def test_customer_get_keeps_orm_for_editing_and_explicit_metrics_read():
    wid, cid = uuid4(), uuid4()
    obj = _customer(wid, cid)
    service = _svc([obj], [])
    assert service.get(wid, cid) is obj
    assert service.get_with_metrics(wid, cid).total_orders == 0
    assert service.get(uuid4(), cid) is None


def test_no_customers_no_bulk_query():
    service = _svc([], [])
    assert service.list(uuid4()) == []
    service.db.execute.assert_not_called()
