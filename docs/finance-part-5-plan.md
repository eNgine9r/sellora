# Finance Part 5 Plan — Epic Sprint 5A

## Goal

Build a practical Finance & Advanced Analytics foundation for Sellora shops so owners can see real operational profit, not only order volume.

## Sprint 5A deliverables

- Finance metrics contract and formulas.
- Read-only backend finance summary service.
- `GET /finance/summary` API endpoint.
- Ukrainian-first `/finance` dashboard MVP.
- Data quality warnings for incomplete source data.
- Regression guardrails that keep Advertising frozen and Meta Ads inactive.

## MVP finance dashboard

The dashboard focuses on:

- revenue;
- gross profit;
- net profit;
- ad spend;
- COGS;
- shipping cost;
- profit margin;
- average order value;
- order counts;
- refunds and other available expenses;
- warnings explaining data quality limitations.

## Advertising dependency rule

Finance uses Advertising data only as conditional manual/CSV source until Advertising runtime/staging blockers are resolved.

Meta Ads API is not active.

## Not accounting software

Sellora Finance MVP is operational profit analytics, not full accounting software. Future work may add expense categories, statement import, tax reports, and deeper accounting workflows, but those are outside Epic Sprint 5A.

## Future improvements

- Dedicated expenses module.
- Refund and discount fields with explicit schema support.
- More detailed finance trend charts.
- Product and campaign profitability breakdowns.
- Exportable finance reports.
- Bank or payment-provider import in a dedicated future sprint.
