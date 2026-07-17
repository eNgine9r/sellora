# Sprint Dd.6 — Advertising, Finance & Analytics Redesign QA

## Pre-implementation audit

### Advertising contract

- Route inspected: `frontend/src/app/advertising/page.tsx`.
- Service contract inspected: `frontend/src/services/advertising.ts` exposes campaigns, metrics, summary, campaign performance and trend endpoints. Every request sends the active workspace through `X-Workspace-ID`.
- Models inspected: campaigns expose platform/status/objective/budget/date fields; metrics expose spend, impressions, reach, clicks, messages, leads, orders, revenue, net profit and calculated CPL/CPA/ROAS/ROI fields.
- Current data source is manual/import-first advertising data. Meta Ads readiness remains represented by the existing readiness card and no live sync claim was added.
- Existing create/edit/archive campaign and add/edit/delete metric flows are preserved. OWNER remains the current frontend editor role for advertising.
- Formula truthfulness: CPL/CPA/ROAS values are displayed only from existing summary/performance/metric fields. Missing denominators render `—` instead of fake zero.

### Finance contract

- Route inspected: `frontend/src/app/finance/page.tsx`.
- Service contract inspected: `fetchFinanceSummary`, `fetchFinanceTrends`, and finance adjustment CRUD endpoints.
- Summary exposes revenue, COGS, gross profit, ad spend, shipping cost, discounts, refunds, other/manual expense components, net profit, margin, orders, AOV, breakdown rows and data-quality warnings.
- Existing net-profit and adjustment formulas remain backend-owned; the UI only displays summary fields and manual adjustment records.
- Manual expense/refund/discount/fee/correction flows are preserved through existing adjustment mutations. OWNER and MANAGER retain mutation controls.

### Analytics contract

- Route inspected: `frontend/src/app/analytics/page.tsx`.
- Analytics uses existing report endpoints for sales, profit, advertising, inventory, customer summaries, business insights and top products, plus existing list services for local report exploration.
- Period selection is provided by the existing shared `DateRangeSelector` / date-range provider.
- Chart/report data remains limited to existing endpoint fields and local workspace-scoped arrays. No new backend report architecture was introduced.
- Analytics remains a deeper report workspace; the page now has a compact summary row but still keeps product, advertising, customer and inventory report sections distinct from Dashboard.

## Implementation decisions

- Advertising, Finance and Analytics now use `WorkspacePage` / `WorkspaceHeader` instead of page-local centered max-width shells.
- Advertising and Finance use explicit five-card `CompactSummary` rows for primary metrics.
- Analytics uses a five-card overview summary sourced from existing sales/customer calculations and report fields.
- Advertising campaign details use `WorkspaceSplitView` + `EntitySidePanel` because campaigns are selectable existing entities.
- Finance has no separate side panel because the current meaningful entity is a manual adjustment displayed/edited inline through the existing form.
- Pagination stays below report/list content: campaign performance, advertising metrics, campaigns, finance adjustments and analytics sales rows.
- Zero vs unavailable: `—` is used for missing or denominator-dependent values; formatted zero is reserved for real calculated zero from the API.
- No fake Meta Ads sync, predictive recommendations, accounting/tax features, or new formulas were added.

## Metric source decisions

### Advertising

- Spend, leads, orders, revenue, CPA/CPL/ROAS: existing advertising summary/performance/metric endpoints.
- Campaign source state: manual/import-first with Meta Ads future/readiness note.
- Campaign detail: existing campaign fields only.

### Finance

- Revenue, COGS, expenses, net profit, AOV and margin: existing finance summary endpoint.
- Expense breakdown: existing summary breakdown rows and finance adjustment records.
- Period comparison: existing finance trends endpoint.

### Analytics

- Orders/revenue/net profit/AOV: existing sales report plus current workspace order rollups where already used.
- Product/customer/advertising/inventory sections: existing report endpoints and existing workspace-scoped lists.
- Repeat/customer metrics: existing customer summary/list rollups; unavailable or restricted values remain explicit.

## Manual QA still required

Authenticated browser QA remains required for `/advertising`, `/finance`, and `/analytics` in light/dark themes across the requested desktop/tablet/mobile viewport matrix. Verify no `NaN`, no `Infinity`, no false zero, no horizontal body scroll, chart readability, bottom pagination, role visibility, and workspace-switch stale data behavior.
