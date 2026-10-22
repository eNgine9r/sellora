from decimal import Decimal
from types import SimpleNamespace

from scripts.backfill_np_order_amounts import (
    SOURCE_COD, SOURCE_DECLARED, amount, fill,
)


def test_amount_disallows_negative_zero_nan_and_extreme_values():
    for sample in (None, "", "0", "-17.00", "NaN", "Infinity", "1000000", "oops"):
        assert amount(sample) is None
    assert amount("749.50") == Decimal("749.50")
    assert amount("749") == Decimal("749.00")


def test_historical_cod_only_dry_run_leaves_revenue_and_profit_unchanged():
    order = SimpleNamespace(
        historical_order_value=None,
        historical_value_source=None,
        revenue=Decimal("0"), net_profit=Decimal("0"), is_historical=True,
    )
    result, totals = fill(
        db=None, workspace_id=None, order_map={"ttn1": order},
        candidates={"ttn1": (Decimal("749.00"), SOURCE_COD)}, dry_run=True,
    )
    assert result["new_NP_COD_REQUESTED"] == 1
    assert totals[SOURCE_COD] == Decimal("749.00")
    assert order.historical_order_value is None
    assert order.revenue == order.net_profit == 0


def test_replay_is_idempotent_and_never_replaces_disputed_source():
    order = SimpleNamespace(
        historical_order_value=Decimal("799.00"), historical_value_source=SOURCE_COD,
        revenue=Decimal("0"), net_profit=Decimal("0"), is_historical=True,
    )
    result, _ = fill(None, None, {"ttn1": order},
                     {"ttn1": (Decimal("799.00"), SOURCE_COD)}, dry_run=True)
    assert result["already_populated"] == 1
    conflict, _ = fill(None, None, {"ttn1": order},
                       {"ttn1": (Decimal("600.00"), SOURCE_DECLARED)}, dry_run=True)
    assert conflict["existing_conflict"] == 1
    assert order.historical_order_value == Decimal("799.00")


def test_backfill_rejects_existing_accounting_entries():
    order = SimpleNamespace(
        historical_order_value=None, historical_value_source=None,
        revenue=Decimal("749.00"), net_profit=Decimal("100.00"), is_historical=True,
    )
    result, _ = fill(None, None, {"ttn1": order},
                     {"ttn1": (Decimal("749.00"), SOURCE_COD)}, dry_run=True)
    assert result["invalid_existing_financial_context"] == 1
    assert order.historical_order_value is None
