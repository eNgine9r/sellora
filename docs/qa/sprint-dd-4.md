# Sprint Dd.4 QA — Orders & Products Redesign

## Implementation summary

- Redesigned `/orders` and `/products` to use the shared Dd.1–Dd.3 CRM workspace foundation: compact headers, tokenized summaries, standardized filter bars, desktop tables, mobile cards, shared entity drawers, loading/empty/error states, and semantic light/dark tokens.
- Preserved backend/API contracts, query keys, auth/session logic, RBAC visibility, workspace scoping, order status workflow, inventory behavior, product/variant mutations, and existing form/dialog flows.

## Orders redesign

- `/orders` now uses `WorkspacePage`, `WorkspaceHeader`, `CompactSummary`, `MetricCard`, and `EntityDrawer`.
- Summary cards use the currently loaded workspace orders from the existing `fetchOrders` query: all orders, new orders, awaiting payment, ready to ship, and problematic orders.
- Filters preserve existing search/status/payment/sort behavior and use tokenized controls.
- Desktop table keeps the existing order actions and now supports selected-row styling; mobile cards remain the mobile experience.
- Order details moved from the squeezed side rail into the shared right drawer/sheet while preserving status change, customer, shipment, item, finance, and history sections.

## Products redesign

- `/products` now uses `WorkspacePage`, `WorkspaceHeader`, `CompactSummary`, tokenized category tabs, filter bar, desktop table, mobile cards, and an entity drawer.
- Summary cards use existing frontend data sources already loaded by the page: products, variants, and inventory.
- The product drawer includes overview, variants, stock, and history tabs. History uses an honest unavailable state because no product history endpoint is exposed in the current frontend flow.
- Product and variant create/edit/archive flows remain unchanged and continue to use the existing dialogs, services, and invalidation patterns.

## Data source limitations / unavailable states

- Orders summary values come from the existing workspace `fetchOrders` response. The current frontend order list is not using server pagination, but future server pagination should move these counts to a workspace-level summary endpoint.
- Products summary values use existing product, variant, and inventory lists. No backend endpoint was added.
- Product history is unavailable through the current frontend/API flow and is shown honestly as unavailable in the drawer.

## Business logic preserved

- No backend files, database schema, migrations, API contracts, backend enums, auth/session logic, RBAC rules, workspace isolation, query-key architecture, order workflow rules, inventory formulas, Nova Poshta logic, Meta Ads gates, or finance formulas were changed.
- OWNER/MANAGER action visibility is preserved; read-only users continue to see read-only states through existing checks.

## Light/dark and mobile requirements

- New/touched Orders and Products surfaces use semantic tokens for canvas, surfaces, borders, text, selected states, inputs, primary/danger actions, and feedback states.
- Mobile cards are preserved for Orders and Products; desktop tables are hidden on mobile breakpoints.
- Drawers use the shared overlay foundation, which provides the existing ESC close, focus trap, focus return, and body scroll lock behavior.

## Manual QA checklist

Manual browser QA remains required for `/orders` and `/products` in both light and dark themes:

- Desktop: 1280×800, 1366×768, 1440×900, 1536×1024, 1920×1080.
- Tablet/mobile: 1024×768, 768×1024, 430×932, 390×844, 375×812.
- Verify no horizontal body scroll.
- Verify filters, tables/cards, pagination, selected rows/cards, drawer tabs, drawer scroll/close/focus, create/edit/archive actions, and status/product forms.
- Verify no regression in auth, RBAC, workspace switching, Sidebar/Topbar, and Dm.1 mobile navigation.

## Automated validation

- `npm run typecheck` — passed.
- `npm run build` — passed with existing non-blocking lint warnings.
- `npm run lint` — passed with existing warnings outside this sprint scope.
- `node frontend/scripts/localization-regression.mjs` — passed.
- `node frontend/scripts/auth-api-boundary-regression.mjs` — passed.
- `node frontend/scripts/mobile-ux-pwa-mvp-regression.mjs` — passed.
- `git diff --check` — passed.

## Sprint status

CONDITIONALLY APPROVED until authenticated browser dual-theme QA and critical Orders/Products flow QA are completed.
