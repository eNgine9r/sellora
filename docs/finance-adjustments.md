# Finance Adjustments — Epic Sprint 5B

Sellora Finance is operational profit analytics, not full accounting or tax reporting.

## Purpose

`finance_adjustments` captures manual expenses, refunds, discounts, fees, shipping adjustments, corrections, and other costs that are not reliably present in orders, shipments, ad metrics, or integrations.

## Supported adjustment types

| Type | Use |
| --- | --- |
| `EXPENSE` | Packaging, tools, rent, salary, and other operating costs |
| `REFUND` | Explicit owner-entered money returned to a buyer |
| `DISCOUNT` | Manual discounts missing from order fields |
| `FEE` | Payment, marketplace, or service fees |
| `SHIPPING_ADJUSTMENT` | Delivery correction not captured by shipment/order cost |
| `CORRECTION` | Manual finance correction |
| `OTHER` | Other owner-entered finance adjustment |

## RBAC policy

- OWNER: full access.
- MANAGER: create, update, and soft-delete operational finance adjustments.
- ANALYST: read-only access.

## Summary impact

Manual adjustments reduce net profit through the updated formula:

```text
Net profit = Revenue - COGS - Ad spend - Shipping cost - Manual expenses - Manual refunds - Manual discounts - Manual fees
```

`SHIPPING_ADJUSTMENT` is included in shipping cost and finance adjustments total.

## Limitations

- Adjustments are manual and may be incomplete.
- They are not a full accounting ledger.
- They do not implement tax reporting, bank import, payment gateway reconciliation, payroll, invoices, or fiscal receipts.
- Migration runtime QA is pending until a safe PostgreSQL runtime is available.
- Advertising data remains a conditional manual/CSV source until runtime/staging blockers are resolved.
- Meta Ads API is not active.

## Epic Sprint 5C stabilization status

Finance adjustments migration has passed static Alembic chain validation, but PostgreSQL runtime migration QA remains pending until tested against a safe staging/test database.

Browser/mobile QA for `/finance` remains pending if no browser runtime is available. Static checks confirm layout markers and guardrail copy, but they are not a substitute for screenshot QA.
