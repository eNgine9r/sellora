from decimal import Decimal
from types import SimpleNamespace

from app.models.order import OrderStatus, PaymentStatus
from app.services.profit_calculation_service import ProfitCalculationService


def order(**overrides):
    values = {
        "status": OrderStatus.COMPLETED.value,
        "payment_status": PaymentStatus.PAID.value,
        "revenue": Decimal("1000"),
        "product_cost": Decimal("300"),
        "ad_cost": Decimal("100"),
        "shipping_cost": Decimal("50"),
        "cod_fee": Decimal("20"),
        "other_cost": Decimal("10"),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_canonical_profit_formula() -> None:
    assert ProfitCalculationService.order_net_profit(order()) == Decimal("520.00")


def test_cancelled_returned_and_refunded_orders_are_excluded() -> None:
    assert ProfitCalculationService.order_net_profit(order(status=OrderStatus.CANCELLED.value)) == Decimal("0.00")
    assert ProfitCalculationService.order_net_profit(order(status=OrderStatus.RETURNED.value)) == Decimal("0.00")
    assert ProfitCalculationService.order_net_profit(order(payment_status=PaymentStatus.REFUNDED.value)) == Decimal("0.00")


def test_included_orders_uses_same_policy_as_profit_calculation() -> None:
    included = order()
    excluded = order(status=OrderStatus.CANCELLED.value)
    assert ProfitCalculationService.included_orders([included, excluded]) == [included]
