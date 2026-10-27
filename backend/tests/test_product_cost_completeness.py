from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
from datetime import datetime, UTC
import hashlib
import json

import pytest

from app.services.profit_calculation_service import ProfitCalculationService
from app.schemas.order import OrderItemCreate, OrderResponse
from app.schemas.order_fulfillment import OrderFulfillmentCreate
from app.services.order_fulfillment_service import OrderFulfillmentService


@pytest.mark.parametrize(
    ("amount", "confirmed", "expected"),
    [
        ("0", None, False),  # Legacy zero is ambiguous.
        ("0", False, False),
        ("0", True, True),  # A deliberately confirmed zero is valid.
        ("125", None, True),  # A legacy positive snapshot was supplied.
        ("125", False, False),
        ("125", True, True),
    ],
)
def test_item_cost_completeness(amount, confirmed, expected):
    item = SimpleNamespace(unit_cost=Decimal(amount), cost_confirmed=confirmed)
    assert ProfitCalculationService.item_cost_known(item) is expected


def test_order_cost_is_unknown_when_any_item_is_unknown():
    known = SimpleNamespace(unit_cost=Decimal("12"), cost_confirmed=True)
    unknown = SimpleNamespace(unit_cost=Decimal("0"), cost_confirmed=None)
    assert ProfitCalculationService.order_cost_known(SimpleNamespace(items=[known, unknown])) is False
    assert ProfitCalculationService.order_cost_known(SimpleNamespace(items=[known])) is True
    assert ProfitCalculationService.order_cost_known(SimpleNamespace(items=[])) is False


def test_order_response_hides_incomplete_profit_without_changing_recorded_values():
    now = datetime.now(UTC)
    ids = [uuid4() for _ in range(4)]
    item = dict(id=ids[0], workspace_id=ids[1], order_id=ids[2], product_variant_id=ids[3],
                sku="synthetic", product_name="Test", quantity=1, unit_price="100", unit_cost="0",
                cost_confirmed=None, line_total="100", line_cost="0")
    data = dict(id=ids[2], workspace_id=ids[1], order_number="QA-1", customer_id=None,
                campaign_id=None, status="NEW", payment_status="COD", revenue="100", product_cost="0",
                ad_cost="0", shipping_cost="0", cod_fee="0", other_cost="0", net_profit="100",
                notes=None, completed_at=None, items=[item], status_history=[], created_at=now, updated_at=now)
    unknown = OrderResponse.model_validate(data)
    assert unknown.product_cost is None and unknown.net_profit is None
    assert data["net_profit"] == "100"  # the original stored snapshot is not rewritten
    item["cost_confirmed"] = True
    confirmed = OrderResponse.model_validate(data)
    assert confirmed.product_cost == Decimal("0") and confirmed.net_profit == Decimal("100")


def test_existing_fulfillment_idempotency_fingerprint_is_preserved():
    payload = OrderFulfillmentCreate(
        idempotency_key="existing-test-key", customer_id=uuid4(), recipient_name="Synthetic",
        recipient_phone="+380671234567", nova_poshta_city_ref="city", city="Test",
        nova_poshta_warehouse_ref="branch", warehouse="Test", create_ttn=False,
        items=[dict(product_variant_id=uuid4(), quantity=1, unit_price="100", unit_cost="0")],
    )
    old_body = payload.model_dump(mode="json", exclude={"idempotency_key", "create_ttn"})
    old_body["items"][0].pop("cost_confirmed")
    expected = hashlib.sha256(json.dumps(old_body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert OrderFulfillmentService._fingerprint(payload) == expected
    payload.items[0].cost_confirmed = True
    assert OrderFulfillmentService._fingerprint(payload) != expected


def test_confirmed_zero_cannot_be_created_by_omitting_the_cost():
    with pytest.raises(ValueError, match="confirmed cost must be supplied"):
        OrderItemCreate(product_variant_id=uuid4(), quantity=1, unit_price=100, cost_confirmed=True)
    item = OrderItemCreate(product_variant_id=uuid4(), quantity=1, unit_price=100, unit_cost=0, cost_confirmed=True)
    assert item.cost_confirmed and item.unit_cost == 0
