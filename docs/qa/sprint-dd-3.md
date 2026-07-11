# Sprint Dd.3 QA — Dashboard, Leads & Customers

## Pre-implementation audit

- Routes reviewed: `/dashboard` in `frontend/src/app/dashboard/page.tsx`, `/leads` in `frontend/src/app/leads/page.tsx`, and `/customers` in `frontend/src/app/customers/page.tsx`.
- Dashboard already uses workspace-scoped query keys and services for dashboard summary, sales/profit summaries, sales trend, advertising summary, orders, leads, inventory summary, shipments, products, and variants.
- Dashboard KPI sources remain server summaries where available: orders/revenue/net profit from `/analytics/dashboard-summary`, sales/profit endpoints, and ROAS from advertising summary. Client-side order filtering is retained only as existing fallback for already-fetched dashboard data.
- Leads use existing `fetchLeads`, `fetchLeadSources`, `createLead`, `updateLead`, and `deleteLead` handlers. Supported filters remain search/status/source; sort remains client-side on the current returned result because no dedicated sort API parameter exists.
- Customers use existing `fetchCustomers`, create/update/archive handlers, and customer completion endpoints for tags, notes, addresses, and attachments. There is no separate customer segment/tag/last-purchase filter API in the current frontend service.
- Dd.3.1 audit: `fetchCustomers` calls `GET /customers` and receives a plain `Customer[]`; the backend route currently has no `limit`, `offset`, `page`, or total metadata parameters, so the current contract is unpaginated. Because this could become paginated later, only the all-customers count is displayed from the returned server list; purchase-segment summaries are marked unavailable until a workspace-level summary endpoint exists.
- Permissions reviewed: OWNER and MANAGER keep edit/archive/create actions in Leads and Customers; read-only states remain for other roles. Backend RBAC remains unchanged.
- No backend, API contract, route, query-key, auth/session, RBAC, or workspace-isolation changes were made.

## Implemented pattern

- Added shared CRM workspace helpers for compact page headers, metric cards, summary rows, toolbar shells, entity drawers, field grids, and drawer tabs.
- Dashboard now starts with a compact protected-page header and period selector instead of a marketing-style gradient hero.
- Leads and Customers now use a shared compact header and summary row before filters and main content.
- Lead and Customer rows open responsive entity drawers based on the shared overlay foundation; mobile lists remain card-based.

## Dashboard notes

| Area | Source / behavior |
| --- | --- |
| Orders KPI | Server dashboard summary first; existing order fallback second. |
| Revenue KPI | Server dashboard/sales summary first; existing order fallback second. |
| Net profit KPI | Owner/Analyst only; unavailable/restricted state for other roles. |
| ROAS KPI | Advertising summary when spend exists; unavailable state otherwise. |
| Attention | Real low-stock, confirmed-order, missing-profit, no-ad-data, or no-period-data conditions only. |
| Funnel | Real leads/orders/delivered counts from existing workspace-scoped data. |
| Charts | Existing Recharts trend/status/category components retained. |

## Leads notes

- Summary row shows server-returned current result counts for all/new/in-progress leads.
- “Needs action” is explicitly unavailable because the current API does not expose a next-action/overdue source of truth.
- Row and mobile card selection opens a drawer with contact, status, source, campaign, assigned state, expected revenue, next action, notes, and current activity limitation.
- Existing create, edit, and archive flows are preserved.

## Customers notes

- Summary row source after Dd.3.1:
  - All customers: uses the current `GET /customers` server-returned list length under the audited unpaginated contract.
  - With purchases, Repeat, No orders: shown as unavailable, because no workspace-level summary source exists and calculating them from returned items would become misleading if/when customer lists are paginated.
- Future backend improvement: expose a workspace-scoped customer summary endpoint with active total, customers with `total_orders >= 1`, repeat customers with `total_orders > 1`, and customers with `total_orders = 0`.
- The customer table remains server-search backed and now opens a shared drawer rather than squeezing a detail rail beside the table.
- Drawer content reuses the existing `CustomerDetails` behavior for tags, notes, addresses, and attachments.
- Existing create, edit, archive, add tag, add note, add address, and add attachment flows are preserved.

## Dual-theme and responsive validation plan

Static implementation uses semantic tokens for the new shared CRM components, Leads/Customers headers, summaries, table containers, selected rows, and CustomerDetails surfaces. Browser verification is still required for both light and dark themes across:

- Desktop: 1280×800, 1366×768, 1440×900, 1536×1024, 1920×1080
- Tablet/mobile: 1024×768, 768×1024, 430×932, 390×844, 375×812

## Automated validation results

- `npm run typecheck` — passed.
- `npm run build` — passed with existing non-blocking lint warnings.
- `npm run lint` — passed with existing warnings outside the Dd.3 scope.
- `node frontend/scripts/localization-regression.mjs` — passed.
- `node frontend/scripts/auth-api-boundary-regression.mjs` — passed.
- `node frontend/scripts/mobile-ux-pwa-mvp-regression.mjs` — passed.
- `git diff --check` — passed.

## Sprint Dd.3.1 closure notes

### Customer summary integrity

- Confirmed customer list contract: frontend `fetchCustomers` returns `Customer[]` from `GET /customers`; backend currently returns a workspace-scoped, unpaginated list with optional search and no total metadata.
- Fix applied: removed current-result calculations for With purchases, Repeat, and No orders from `/customers`; these metrics now render an honest unavailable state.
- The customer summary no longer changes these purchase-segment values when list ordering/search result composition changes, and it will not silently become page-derived if pagination is introduced later.

### Runtime / browser QA

- Browser runtime, authenticated workspace credentials, and multi-role test accounts are not available inside this container.
- Required themes remain pending: light and dark.
- Required viewports remain pending: 1280×800, 1366×768, 1440×900, 1536×1024, 1920×1080, 1024×768, 768×1024, 430×932, 390×844, 375×812.
- Required roles remain pending: OWNER, MANAGER, ANALYST.
- Required CRM flows remain pending in browser: dashboard period/widget checks; leads search/filter/sort/pagination/drawer/create/edit/archive/assignment/conversion/order creation when supported; customers search/sort/pagination/drawer/create/edit/archive/tags/notes/addresses/attachments; workspace switching stale-data check.

## Manual QA still required

- Authenticated browser QA for `/dashboard`, `/leads`, and `/customers` in light and dark themes.
- Critical CRM flows against a live backend: lead create/edit/archive, lead drawer open, customer create/edit/archive, customer notes/tags/addresses/attachments, and workspace switch stale-data check.
- Viewport measurement for no horizontal body scroll.

## Sprint status

CONDITIONALLY APPROVED until browser-based dual-theme and critical CRM flow QA is completed.
