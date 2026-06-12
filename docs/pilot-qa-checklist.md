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

## Sprint 2.8 feedback and release checks

[ ] Action: Open the Feedback form from the topbar.
Expected result: Category, optional rating, required message, current page and privacy hint are visible.
Notes:
Severity if failed:

[ ] Action: Submit feedback with an empty message.
Expected result: Submit is blocked or validation appears.
Notes:
Severity if failed:

[ ] Action: Submit valid feedback.
Expected result: Loading state appears, then localized success message appears.
Notes:
Severity if failed:

[ ] Action: Open `/settings/feedback` as owner/manager.
Expected result: Workspace-scoped feedback list appears without raw internal IDs in the primary UI.
Notes:
Severity if failed:

[ ] Action: Review known limitations and pilot release notes with the pilot user.
Expected result: User understands what is manual, what is not automated yet, and how to report problems safely.
Notes:
Severity if failed:

## Sprint 2.9 Pilot QA Addendum — Mobile polish and orders pagination

- [ ] Open the mobile sidebar at 375px.
Expected result: profile, language, theme and logout controls are compact; email is truncated and does not stretch the drawer.
Notes:
Severity if failed: Major

- [ ] Open the app topbar at 375px.
Expected result: topbar stays on one row; feedback/language/theme are available from the More menu.
Notes:
Severity if failed: Major

- [ ] Select “Власний період” / “Custom period” on Dashboard.
Expected result: date fields do not overflow and calendar icons are visible in dark and light themes.
Notes:
Severity if failed: Major

- [ ] Open the Feedback form on desktop and mobile.
Expected result: centered modal on desktop, bottom sheet on mobile, overlay visible, submit/cancel accessible.
Notes:
Severity if failed: Major

- [ ] Open “Звіти” from sidebar.
Expected result: route opens the Analytics reports page without duplicate or blank reports screens.
Notes:
Severity if failed: Major

- [ ] Open /orders with more than 5 orders.
Expected result: first page shows 5 orders, page sizes 5 / 15 / 30 work, search/filter/sort reset pagination to page 1.
Notes:
Severity if failed: Major

- [ ] Re-test Analytics detailed table pagination.
Expected result: /analytics shows 5 detailed rows by default, page sizes 5 / 15 / 30 work, and changing the local period resets pagination to page 1.
Notes:
Severity if failed: Major

- [ ] Confirm there is no global period selector in the shared topbar.
Expected result: Dashboard and Analytics still have local period selectors, but the shared header no longer duplicates this control.
Notes:
Severity if failed: Minor
