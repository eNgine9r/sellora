## ProfitCalculationService.components in backend/app/services/profit_calculation_service.py (L72-L83)

**Purpose:** Canonical order-derived revenue/cost components shared by profit and Finance.

**Inputs & Assumptions:**
- order: trusted persisted order or caller-supplied protocol object with status, payment_status and financial snapshots (L13-L21).
- Currency and cost completeness are not validated here; Finance records missing-cost and spend-allocation warnings separately (`finance_service.py:L149-L201`).
- Fully paid/delivered realization before inclusion: **nothing found**. Included statuses explicitly include NEW and CONFIRMED (profit L52-L60).

**Outputs & Effects:** Immutable ProfitComponents value; no DB/provider side effects. Excluded order returns zero for all components (L74-L75).

**Block-by-Block:**

```python
# L74-L83
if not cls.includes_order(order):
    return ProfitComponents(MONEY_ZERO, MONEY_ZERO, MONEY_ZERO, MONEY_ZERO, MONEY_ZERO, MONEY_ZERO)
return ProfitComponents(
    revenue=cls.money(order.revenue),
    product_cost=cls.money(order.product_cost),
    advertising_cost=cls.money(order.ad_cost),
    delivery_cost=cls.money(order.shipping_cost),
    payment_fees=cls.money(order.cod_fee),
    other_cost=cls.money(order.other_cost),
)
```

- **What:** Excludes cancelled/returned/refunded orders by predicate; otherwise projects stored per-order fields.
- **Why here:** One exclusion predicate precedes all calculations, so both revenue and costs follow the same inclusion boundary.
- **Assumes:** Stored allocated costs represent desired order economics; campaign spend reconciliation is outside.
- **Establishes:** Included components all rounded to 2 decimal places; excluded orders contribute neither revenue nor original ad/delivery costs.

**Cross-Function Dependencies:**
- includes_order (L67-L70): missing status becomes NEW, missing payment becomes PENDING; valid status and payment != REFUNDED.
- money (L62-L64): Decimal(value or 0), ROUND_HALF_UP, two decimals.
- ProfitComponents.net_profit (L35-L46): subtracts product/ad/delivery/payment/other/refunds/returns.
- order_net_profit (L85-L87) delegates components.net_profit.
- included_orders (L89-L91) filters with same predicate; Finance calls it (`finance_service.py:L167`), sums order.ad_cost (L177), contrasts campaign spend in warning only (L178-L185), and applies manual expense/refund/shipping adjustments (L198-L220).

**Open Questions:**
- Should the UI explicitly call NEW/CONFIRMED order profit estimated rather than realized?
- How should irrecoverable advertising, failed-delivery and return fees remain in shop P&L when original order is excluded? Current Finance uses manual adjustment warnings at L203-L216.
- When should COD be considered collected? Finance treats PAID and COD as paid-count statuses (`finance_service.py:L29,L222`).
