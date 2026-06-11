# Sellora Analytics Metrics Source of Truth

Sprint 2.4 defines the MVP analytics formulas used by Dashboard and Analytics/Reports. Backend enum values remain English API/DB values; localization happens only in the frontend display layer.

## Period behavior

- Reports use the selected `date_from` and `date_to` range from the shared date range selector.
- Date filters are inclusive by calendar date.
- The previous comparison period is the equivalent number of days immediately before the selected period.
- `All time` does not show previous-period comparison because there is no meaningful equivalent historical range.
- Custom ranges without valid dates show empty/unavailable states instead of unsafe calculations.

## Revenue

```text
Revenue = sum(order.revenue) for orders created in the selected period
```

Included order statuses for report/Dashboard revenue:

```text
NEW
CONFIRMED
SHIPPED
DELIVERED
COMPLETED
```

Excluded order statuses:

```text
CANCELLED
RETURNED
```

Cancelled and returned orders are still counted in status breakdowns, return/cancellation metrics, and operational insights.

## Net profit

```text
net_profit = revenue - product_cost - ad_cost - shipping_cost - cod_fee - other_cost
```

Financial/profit values are role-sensitive. If the current role is not allowed to view profit analytics, UI must show a localized restricted state and avoid rendering profit, margin, product cost, or profit trend values.

## Gross profit and margin

```text
gross_profit = revenue - product_cost
margin = net_profit / revenue
```

If revenue is zero, margin is displayed as unavailable (`—`).

## Orders count

Dashboard and Sales Report order count means:

```text
orders created in the selected period
```

Reports also show status and payment breakdowns so owners can separate created, delivered, completed, returned, and cancelled orders.

## AOV

```text
AOV = revenue / included_orders_count
```

If included order count is zero, AOV is displayed as unavailable (`—`).

## Advertising metrics

```text
ROAS = ad_revenue / ad_spend
CPA = ad_spend / ad_orders
CPL = ad_spend / ad_leads
```

If a denominator is zero, the metric is unavailable (`—`) rather than `0`, `NaN`, or `Infinity`.

Optional imported metrics follow standard formulas when source data exists:

```text
CTR = clicks / impressions
CPM = ad_spend / impressions * 1000
CPC = ad_spend / clicks
```

## Conversion and customer metrics

```text
lead_to_order_conversion = converted_leads / total_leads
repeat_customer_rate = customers_with_2_plus_orders / customers_with_orders
average_spend_per_customer = total_spent / customers_with_orders
```

If a denominator is zero, display `—`.

## Return rate

```text
return_rate = returned_orders / (shipped_orders + delivered_orders + completed_orders + returned_orders)
```

If the denominator is zero, display `—`.

## Inventory metrics

```text
low_stock = stock_quantity <= minimum_quantity
out_of_stock = stock_quantity <= 0
reserved_stock = sum(reserved_quantity)
incoming_stock = sum(incoming_quantity)
```

Inventory reports combine current stock state with selected-period product sales so users can identify best sellers that need replenishment.

## Business insights

Sprint 2.4 insights are deterministic rule-based checks from existing data. They do not use AI and they do not invent events.

Current insight rules include:

- Low stock needs attention when one or more variants are at or below minimum stock.
- Ad spend without orders when advertising spend exists but advertising orders are zero.
- ROAS below 1 when advertising revenue is lower than spend.
- Returns/cancellations review when returned or cancelled orders exist.
- Leads not converting when leads exist but no orders exist in the same period.
- Healthy state when no urgent rules fire.

Each insight includes a type, title, description, source metric, and optional CTA.

## Dashboard/report consistency

The Dashboard and Analytics/Reports share formula helpers in `frontend/src/lib/analytics-formulas.ts` so period filters, included statuses, zero denominator behavior, revenue, AOV, ROAS/CPA/CPL, return rate, inventory alerts, and insight rules do not drift.

Expected consistency checks:

- Dashboard revenue for a period equals Sales Report revenue for the same period.
- Dashboard ROAS uses the same safe advertising formula as Advertising Report.
- Dashboard top product/category logic uses the same product/category period data as Product Report.
- Dashboard low-stock alerts use the same low-stock rule as Inventory Report.

## Edge case behavior

The UI must never render unsafe values such as:

```text
NaN
Infinity
undefined
null
```

Use `—`, a localized restricted state, or a localized empty state for missing data, zero denominators, empty ranges, products without images/categories, orders without customers/items, campaigns without metrics, and historical imported orders.
