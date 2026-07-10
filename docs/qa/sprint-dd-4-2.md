# Sprint Dd.4.2 QA — Dashboard Reference Implementation & Embedded Detail Panels

## Implementation summary

- Added true shared protected-workspace side-panel primitives: `WorkspaceSplitView` and `EntitySidePanel`.
- `EntitySidePanel` renders as a non-modal desktop `<aside>` with no backdrop, no blur, no body scroll lock, and no modal focus trap; below `lg` it reuses the standard modal `Drawer` so mobile remains an accessible sheet.
- Restored standard `Drawer` modal behavior for genuine drawer usages; entity details use the responsive side-panel abstraction instead of changing all drawers globally.
- Replaced generic auto-fit summary behavior with count-aware balanced layouts. Five-card summaries use a 3 + 2 layout on medium desktop, five equal columns on wide desktop, and deliberate tablet spans.
- Dashboard cleanup keeps the reference-oriented operational structure and prevents setup/onboarding from dominating established workspaces.

## Dashboard final layout

- Compact header with the existing period selector.
- Four primary KPI cards: orders, revenue, net profit, and ROAS/ad spend.
- Operational rows retain real needs-attention, sales funnel, revenue/profit trend, order status breakdown, advertising, inventory, recent orders, notifications, and activity blocks.
- Setup/onboarding is only shown for first-run workspaces and no longer dominates established workspace first view.

## Dashboard data-source decisions

- Orders, revenue, profit, and advertising metrics continue to use existing workspace-scoped analytics/order queries.
- Inventory and notifications continue to use existing workspace-scoped dashboard/inventory/shipment sources.
- No fake metrics, fake history, or new backend-derived values were introduced.

## Embedded side-panel behavior

- Desktop entity details are rendered as a sibling layout column through `WorkspaceSplitView` / `EntitySidePanel` where entity pages use the shared `EntityDrawer` compatibility surface.
- Desktop side panels use `<aside aria-labelledby>` semantics, independent internal scroll, close action, and no modal backdrop/focus trap.
- Mobile and tablet keep the modal Drawer sheet with ESC/focus lifecycle through the existing overlay foundation.

## Balanced KPI rules

- Five-card summary sections use six columns at medium desktop: first three cards span two columns, last two span three columns.
- Wide desktop uses five equal columns.
- Tablet odd final cards intentionally span both columns.

## Create Order selector regression

- Dd.4.1 selector improvements are preserved: semantic controls, compact option rows, bounded product list height, 32px thumbnails, truncation, and light/dark readable selected/hover states.

## Manual QA still required

- Routes: `/dashboard`, `/orders`, `/products`, `/leads`, `/customers`.
- Themes: light and dark.
- Desktop: 1280×800, 1366×768, 1440×900, 1536×1024, 1920×1080.
- Tablet/mobile: 1024×768, 768×1024, 430×932, 390×844, 375×812.
- Verify no excessive gutter, no orphan KPI cards, desktop side panel does not cover tables, mobile sheet remains accessible, and Create Order selectors remain polished.

## Automated validation

- `npm run typecheck` — passed.
- `npm run build` — passed with existing non-blocking warnings.
- `npm run lint` — passed with existing warnings outside Dd.4.2 scope.
- `node frontend/scripts/localization-regression.mjs` — passed.
- `node frontend/scripts/auth-api-boundary-regression.mjs` — passed.
- `node frontend/scripts/mobile-ux-pwa-mvp-regression.mjs` — passed.
- `git diff --check` — passed.

## Sprint status

CONDITIONALLY APPROVED until authenticated browser visual QA verifies dashboard and side-panel behavior.
