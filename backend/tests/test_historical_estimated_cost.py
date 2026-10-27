"""Advisory historical landed COGS must never alter accounting or inventory."""
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.order import Order
from app.models.order_item import OrderItem
from app.schemas.order import HistoricalCostConfidence, HistoricalCostSource, HistoricalEstimatedCostUpsert
from app.services.order_service import OrderService, OrderServiceError


class FakeDB:
    def __init__(self):
        self.commits = 0
        self.refreshes = 0

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        self.refreshes += 1


class FakeOrderRepository:
    def __init__(self, order):
        self.order = order

    def get_for_update(self, workspace_id, order_id):
        if self.order.workspace_id == workspace_id and self.order.id == order_id and self.order.deleted_at is None:
            return self.order
        return None

    get = get_for_update


class FakeAudit:
    def __init__(self):
        self.events = []

    def create(self, **kwargs):
        self.events.append(kwargs)


def make_service(*, historical=True, confirmed_cost="0"):
    workspace_id, order_id = uuid4(), uuid4()
    order = Order(
        id=order_id, workspace_id=workspace_id, order_number="NP-TEST",
        is_historical=historical, status="DELIVERED", payment_status="PENDING",
        revenue=Decimal("0"), product_cost=Decimal(confirmed_cost),
        net_profit=Decimal("0"), ad_cost=Decimal("0"), shipping_cost=Decimal("0"),
        other_cost=Decimal("0"), cod_fee=Decimal("0"),
    )
    order.items = []
    order.status_history = []
    service = OrderService.__new__(OrderService)
    service.db = FakeDB()
    service.orders = FakeOrderRepository(order)
    service.audit_logs = FakeAudit()
    return service, order


def estimate(amount="130.00", source=HistoricalCostSource.SHEET_ROW_MATCH, reference="Sheet row 4175"):
    return HistoricalEstimatedCostUpsert(amount=Decimal(amount), source=source, reference=reference)


def test_estimate_is_separate_from_financial_accounting_and_audited():
    service, order = make_service()
    baseline = (order.revenue, order.product_cost, order.net_profit, order.payment_status, order.status)
    result = service.set_historical_cost_estimate(order.workspace_id, order.id, estimate(), uuid4())
    assert result is order
    assert order.estimated_product_cost == Decimal("130.00")
    assert order.estimated_cost_source == "SHEET_ROW_MATCH"
    assert order.estimated_cost_confidence == HistoricalCostConfidence.MULTI_SIGNAL_MATCH.value
    assert order.estimated_cost_reference == "Sheet row 4175"
    assert (order.revenue, order.product_cost, order.net_profit, order.payment_status, order.status) == baseline
    assert service.db.commits == 1
    assert service.audit_logs.events[0]["action"] == "HISTORICAL_COST_ESTIMATE_SET"
    assert service.audit_logs.events[0]["new_value"]["estimated_product_cost"] == "130.00"


def test_estimate_update_and_clear_preserves_finance_and_has_audit_trail():
    service, order = make_service()
    actor = uuid4()
    service.set_historical_cost_estimate(order.workspace_id, order.id, estimate(), actor)
    service.set_historical_cost_estimate(order.workspace_id, order.id, estimate("140", HistoricalCostSource.PRICE_MEDIAN, None), actor)
    assert order.estimated_cost_confidence == "PRICE_ONLY"
    service.clear_historical_cost_estimate(order.workspace_id, order.id, actor)
    assert order.estimated_product_cost is None
    assert order.estimated_cost_source is None
    assert order.estimated_cost_reference is None
    assert [e["action"] for e in service.audit_logs.events] == [
        "HISTORICAL_COST_ESTIMATE_SET", "HISTORICAL_COST_ESTIMATE_SET",
        "HISTORICAL_COST_ESTIMATE_CLEARED",
    ]
    assert service.audit_logs.events[-1]["old_value"]["estimated_product_cost"] == "140"
    assert order.net_profit == Decimal("0")
    assert order.product_cost == Decimal("0")


@pytest.mark.parametrize("historical,confirmed", [(False, "0"), (True, "125")])
def test_normal_or_confirmed_cost_orders_cannot_receive_estimates(historical, confirmed):
    service, order = make_service(historical=historical, confirmed_cost=confirmed)
    with pytest.raises(OrderServiceError):
        service.set_historical_cost_estimate(order.workspace_id, order.id, estimate(), uuid4())
    assert service.db.commits == 0
    assert service.audit_logs.events == []


def test_wrong_workspace_or_missing_order_cannot_receive_estimate():
    service, order = make_service()
    assert service.set_historical_cost_estimate(uuid4(), order.id, estimate(), uuid4()) is None
    assert service.clear_historical_cost_estimate(uuid4(), order.id, uuid4()) is None
    assert service.db.commits == 0
    assert service.audit_logs.events == []


def test_exact_row_matching_requires_source_reference():
    service, order = make_service()
    with pytest.raises(OrderServiceError, match="reference is required"):
        service.set_historical_cost_estimate(order.workspace_id, order.id, estimate(reference="  "), uuid4())
    assert service.db.commits == 0


@pytest.mark.parametrize("value", ["0", "-1", "23.123", "10000000000"])
def test_rejects_invalid_monetary_amount(value):
    with pytest.raises(ValidationError):
        estimate(amount=value)


def test_estimate_source_confidence_is_canonical_and_cannot_be_faked():
    service, order = make_service()
    service.set_historical_cost_estimate(
        order.workspace_id, order.id,
        estimate("120", HistoricalCostSource.PRICE_BAND, None), uuid4(),
    )
    assert order.estimated_cost_confidence == "LOW"
    with pytest.raises(ValidationError):
        HistoricalEstimatedCostUpsert(amount=100, source="CONFIRMED_BANK_PAYMENT")


def test_estimate_cannot_override_nonzero_item_cost_even_if_order_aggregate_zero():
    service, order = make_service()
    order.items = [OrderItem(
        id=uuid4(), workspace_id=order.workspace_id, order_id=order.id,
        product_variant_id=uuid4(), sku="ARCHIVE-SKU", product_name="Watch",
        quantity=1, unit_price=Decimal("0"), unit_cost=Decimal("25.00"),
        line_total=Decimal("0"), line_cost=Decimal("25.00"),
    )]
    with pytest.raises(OrderServiceError):
        service.set_historical_cost_estimate(order.workspace_id, order.id, estimate(), uuid4())
    assert service.db.commits == 0
