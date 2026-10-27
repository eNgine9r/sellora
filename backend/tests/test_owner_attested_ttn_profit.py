from decimal import Decimal
from types import SimpleNamespace

from app.services.profit_calculation_service import ProfitCalculationService


def order(*, cost="0", attested=True):
    return SimpleNamespace(
        is_historical=True, status="COMPLETED", payment_status="PAID",
        revenue=Decimal("679"), product_cost=Decimal(cost),
        ad_cost=Decimal("0"), shipping_cost=Decimal("0"), cod_fee=Decimal("0"), other_cost=Decimal("0"),
        historical_value_evidence={"owner_attestation": {"profit_cost_status": "UNKNOWN"}} if attested else {},
    )


def test_unknown_landed_cost_must_not_be_reported_as_full_sales_profit():
    assert ProfitCalculationService.order_net_profit(order()) == Decimal("0.00")


def test_confirmed_landed_cost_enables_normal_profit_calculation():
    assert ProfitCalculationService.order_net_profit(order(cost="125")) == Decimal("554.00")


def test_owner_attested_order_can_confirm_an_explicit_zero_cost():
    historical = order()
    historical.items = [SimpleNamespace(unit_cost=Decimal("0"), cost_confirmed=True)]
    assert ProfitCalculationService.order_net_profit(historical) == Decimal("679.00")


def test_original_order_calculation_does_not_change_without_owner_attestation():
    assert ProfitCalculationService.order_net_profit(order(attested=False)) == Decimal("679.00")
