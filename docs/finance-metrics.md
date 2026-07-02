# Finance Metrics MVP — Epic Sprint 5A

Sellora Finance MVP is operational profit analytics, not full accounting software. It helps an Instagram shop owner understand whether orders are turning into real profit.

## Scope

Finance 5A is a read-only metrics foundation:

- revenue;
- product cost / COGS;
- gross profit;
- advertising spend;
- shipping cost;
- discounts;
- refunds;
- other available order-level expenses;
- net profit;
- profit margin;
- average order value.

It does not implement payment gateway integration, bank statement import, tax accounting, or full бухгалтерія.

## Data sources

| Metric | Source | Status |
| --- | --- | --- |
| Revenue | Sellora orders with valid statuses | Active MVP source |
| COGS | Order item cost snapshots or order product cost fallback | Active with data-quality warning when missing |
| Ad spend | Manual/CSV `ad_metrics.spend` only | Conditional source |
| Shipping cost | Shipment cost when available, order shipping fallback otherwise | Conditional source |
| Discounts | Not available in current schema | Treated as 0 with warning |
| Refunds | Cancelled/returned/refunded orders excluded from valid revenue | Reported as 0 to avoid double-counting |
| Other expenses | Order COD fee and order-level other cost | Limited MVP source |

Finance uses Advertising data only as conditional manual/CSV source until Advertising runtime/staging blockers are resolved.

Meta Ads API is not active.

## Formulas — English

```text
Revenue = sum of valid order totals
COGS = sum of product/variant cost from order items
Gross profit = revenue - COGS
Ad spend = manual/CSV advertising spend for selected period
Shipping cost = shipment cost if available, otherwise order shipping fallback or unknown
Discounts = discount value if available, otherwise 0 with warning
Refunds = 0 when cancelled/refunded orders are excluded from revenue to avoid double-counting
Net profit = revenue - COGS - ad spend - shipping cost - discounts - refunds - other expenses
Profit margin = net profit / revenue
Average order value = revenue / paid_or_valid_orders_count
```

## Формули — українською

```text
Дохід = сума валідних замовлень
Собівартість товарів (COGS) = сума собівартості позицій замовлень
Валовий прибуток = дохід - собівартість товарів
Витрати на рекламу = ручні або CSV-рекламні витрати за вибраний період
Доставка = вартість відправлення, якщо доступна, або fallback із замовлення
Знижки = значення знижок, якщо доступне; інакше 0 з попередженням
Повернення = 0, якщо скасовані/повернені замовлення вже виключені з доходу
Чистий прибуток = дохід - собівартість - реклама - доставка - знижки - повернення - інші витрати
Маржа прибутку = чистий прибуток / дохід
Середній чек = дохід / кількість оплачених або валідних замовлень
```

## Safety rules

- Workspace isolation is mandatory for every finance query.
- Finance summary is read-only and must not write to the database.
- Values with zero denominator return unavailable metadata so the UI can show `—` instead of NaN or Infinity.
- Cancelled, returned, and refunded orders are excluded from valid revenue to avoid double-counting refunds.
- Meta Ads live sync, OAuth, token storage, and apply-sync are not used.
- Advertising remains feature-frozen and not pilot-ready.

## Data quality warnings

Finance responses include owner-facing warnings when:

- no valid orders exist for the selected period;
- product costs are missing;
- shipment costs are missing;
- advertising data is manual/CSV only;
- Meta Ads API is not active;
- discounts are not available in the current schema;
- full accounting expenses are not available.
