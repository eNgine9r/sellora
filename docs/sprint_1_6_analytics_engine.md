# Sprint 1.6 Analytics Engine

Sprint 1.6 transforms existing Sellora CRM, order, product, customer, and inventory data into workspace-scoped business insights.

## Backend

- `AnalyticsRepository` owns workspace-scoped reads for orders, order items, customers, and inventory joins.
- `AnalyticsService` owns calculations for sales summaries, profit summaries, sales trends, top products, customer summaries, inventory summaries, and dashboard aggregates.
- `/api/v1/analytics/*` exposes read-only endpoints with date range filtering. If dates are omitted, analytics default to the last 30 days.

## RBAC

- `OWNER` and `ANALYST` can read profit-bearing endpoints.
- `MANAGER` can read non-profit sales, customer, and inventory analytics only.
- Profit-bearing endpoints use an explicit `OWNER`/`ANALYST` guard until a more granular permission system exists.

## Out of scope

- Google Sheets import
- Meta Ads API
- Nova Poshta API
- Advertising analytics
- AI insights
