from decimal import Decimal
from types import SimpleNamespace

from app.models.order import Order
from app.services.order_service import OrderService


def test_fulfillment_draft_does_not_recognize_extra_finance() -> None:
    order = Order(revenue=Decimal("100.00"), product_cost=Decimal("40.00"), ad_cost=Decimal("10.00"), shipping_cost=Decimal("0"), cod_fee=Decimal("0"), other_cost=Decimal("0"))
    OrderService(SimpleNamespace())._recalculate_profit(order)
    assert order.net_profit == Decimal("50.00")
