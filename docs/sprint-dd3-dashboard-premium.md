# Sellora — Dd.3 Dashboard premium UI

Status: implementation on feature branch, staged deployment pending.

## Scope

- Preserve /dashboard, shared date range, API queries, RBAC, workspace context, calculations and localization.
- Promote KPIs and revenue/profit chart; avoid misleading zero values while data is loading.
- Convert owner alerts to compact actionable links. Remove repeated NotificationsCard on Dashboard (other modules are unchanged).
- Render lead/order/delivered stages as compact bars using observed counts, not demo numbers. A ratio of separate lead and order counts is NOT an attributed conversion rate.
- Add specific empty state if orders exist without recorded financial revenue. Manager with no profit privilege sees restricted chart instead of empty sales.
- Compact first-run checklist behind a disclosure without removing its steps.
- Refresh Dashboard-local ChartCard and activity styling using existing design tokens.
- Preserve light/dark and uk/en.

## Validation checklist

- [x] TypeScript checked locally (initial pass)
- [x] Frontend production build (initial pass)
- [x] Existing Sprint 7C owner experience static regression
- [x] Dd.3 regression script and final typecheck (production build earlier passed)
- [ ] Mobile browser visual QA on staging preview
- [ ] OWNER / MANAGER / ANALYST authenticated browser QA
- [ ] Public staging deploy and smoke test

## Known pre-existing testing gap

The legacy frontend/scripts/dashboard-analytics-regression.mjs checks for previousSalesSummary, topCategories, and dashboard logistics markers which are not present on the baseline main Dashboard page. This legacy test fails independently of Dd.3 and should be updated in a separate tests-maintenance scope. The Dd.3 regression tests actual existing and new behavior.

## Release guard

Do not mark GREEN/ready to update until deployed preview or staging is checked with real browser sessions and no authorization/data issues.
