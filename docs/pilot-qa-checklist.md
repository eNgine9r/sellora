# Sellora Pilot QA Checklist

Формат для кожної перевірки:

```text
[ ] Action:
Expected result:
Notes:
Severity if failed:
```

## Core access

[ ] Action: Login to staging/demo account.
Expected result: User lands in Sellora app without errors.
Notes:
Severity if failed:

[ ] Action: Switch language UA/EN.
Expected result: Labels change, backend enum values remain English in API-facing data.
Notes:
Severity if failed:

[ ] Action: Toggle dark/light theme.
Expected result: Text and cards remain readable.
Notes:
Severity if failed:

## Demo workspace

[ ] Action: Run `cd backend && python scripts_seed_demo.py` twice.
Expected result: Demo data exists and no duplicate DEMO records are created.
Notes:
Severity if failed:

[ ] Action: Open Dashboard in demo workspace.
Expected result: Demo badge appears, revenue/orders/top products/inventory alerts are meaningful, no NaN/Infinity.
Notes:
Severity if failed:

## Empty workspace onboarding

[ ] Action: Open Dashboard in a new/empty workspace.
Expected result: Setup checklist and useful first-run CTAs are visible.
Notes:
Severity if failed:

[ ] Action: Click each setup checklist CTA.
Expected result: Products, orders, advertising, integrations, import and analytics links navigate correctly.
Notes:
Severity if failed:

## Modules

[ ] Action: Open Products.
Expected result: Product list or action-oriented empty state appears.
Notes:
Severity if failed:

[ ] Action: Open Orders.
Expected result: Orders list or action-oriented empty state appears.
Notes:
Severity if failed:

[ ] Action: Open Inventory.
Expected result: Stock, low stock and out-of-stock states are understandable.
Notes:
Severity if failed:

[ ] Action: Open Customers and Leads.
Expected result: Lists or empty states explain next actions.
Notes:
Severity if failed:

[ ] Action: Open Shipments and Advertising.
Expected result: Lists/metrics or clear empty states appear.
Notes:
Severity if failed:

[ ] Action: Open Analytics.
Expected result: Reports load from real/demo data and no unavailable ratio shows NaN/Infinity.
Notes:
Severity if failed:

## Import Center

[ ] Action: Open `/settings/import`.
Expected result: Import helper explains dry-run, warnings, errors and duplicates.
Notes:
Severity if failed:

[ ] Action: Run product catalog dry-run with synthetic file.
Expected result: Counters, row-level warnings/errors and duplicate behavior are readable.
Notes:
Severity if failed:

## Mobile QA

[ ] Action: Check Dashboard, Orders, Products, Inventory, Analytics, Import Center at 375px, 390px, 430px and 768px.
Expected result: No body-level horizontal overflow; topbar, cards, tables and import actions remain usable.
Notes:
Severity if failed:
