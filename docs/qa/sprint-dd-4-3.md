# Sprint Dd.4.3 — Dashboard Reference Rebuild & Split View Integration Closure

## Pre-implementation audit

- `WorkspaceSplitView` and `EntitySidePanel` existed in `frontend/src/components/crm-workspace.tsx`, but the entity routes were still rendering detail content after the table/list through `EntityDrawer` compatibility usage.
- `/orders`, `/products`, `/leads`, and `/customers` did not use the split-view component as the actual route-level parent for the list/table and detail panel.
- Orders and Products had five-card summaries, but they did not explicitly opt into a named five-card layout API.
- The protected desktop shell used a fixed sidebar plus a topbar in the content column, so the desktop header row was visually disconnected from the sidebar brand area.

## Dashboard final layout

`/dashboard` now follows the approved compact operational reference structure:

1. Compact `WorkspaceHeader` with one `DateRangeSelector`.
2. Primary four-card KPI row: Orders, Revenue, Net profit, ROAS.
3. Operational row: Needs attention and Sales funnel.
4. Analytics row: Revenue/net-profit trend and Order status breakdown.
5. Business row: Advertising and Inventory cards.
6. Operational lists: Recent orders, Notifications, Activity.
7. Secondary lower content: Top products and Quick actions.
8. First-run onboarding remains below operational content and only appears for empty first-run workspaces.

## Dashboard data-source decisions

- Orders, revenue, net profit, ROAS, advertising, inventory, order status, recent orders, activity, and notifications continue to use existing workspace-scoped dashboard, analytics, orders, leads, inventory, shipments, products, variants, and advertising queries.
- No fake metrics were added.
- Profit remains hidden or unavailable when the current role cannot see it or when required cost data is missing.
- Funnel conversion remains period-scoped and is shown only when the denominator exists; otherwise the UI shows the existing unavailable helper.

## Removed or consolidated sections

- Removed the oversized owner-context explanatory card from the main dashboard viewport.
- Consolidated duplicate advertising and inventory blocks into one compact business row.
- Removed the old fulfillment/finance/logistics card row from the primary viewport to keep the Dashboard focused on daily operations.
- Kept Top products and Quick actions as secondary lower content rather than first-viewport content.

## WorkspaceSplitView route integrations

- `/orders`: `WorkspaceSplitView` wraps the order table/pagination content and receives the selected order detail panel through its `panel` prop.
- `/products`: `WorkspaceSplitView` wraps the product table, pagination, and variant management content, with the selected product detail panel as the right-side sibling column.
- `/leads`: `WorkspaceSplitView` wraps lead loading/empty/error/table states, with the selected lead panel as the right-side sibling column.
- `/customers`: `WorkspaceSplitView` wraps customer loading/empty/error/table states, with the selected customer tabs/details as the right-side sibling column.

## Desktop versus mobile detail behavior

- Desktop (`lg` and wider): entity detail content renders as a non-modal `<aside>` in the second split-view grid column. It has no backdrop, no blur, no body scroll lock, no modal focus trap, and no `aria-modal`.
- Mobile/tablet below `lg`: the same detail content falls back to the existing modal `Drawer`, preserving backdrop, body scroll lock, focus trap, Escape close, and focus return semantics.
- Generic Drawer behavior was not globally changed; create/edit forms, confirmations, mobile menus, and other overlay flows remain modal.

## Balanced KPI grid rules

- `CompactSummary` now exposes an explicit `layout="five-balanced"` option.
- Orders and Products both opt into the five-card layout explicitly.
- Five-card summaries use:
  - one column on mobile;
  - two columns on tablet with the last card intentionally spanning both columns;
  - a six-column `3 + 2` layout on medium desktop;
  - five equal columns on wide desktop.

## Protected shell alignment

- Desktop App Shell now uses a two-row/two-column CSS grid with shared `--sidebar-width` and `--topbar-height` variables.
- The brand/logo cell and topbar use the same height and aligned bottom border.
- Sidebar navigation begins below the unified header row.
- Mobile shell behavior, mobile drawer, and bottom navigation remain unchanged.

## Automated regression guard

Added `frontend/scripts/sprint-dd-4-3-regression.mjs` to statically verify:

- Dashboard required section structure;
- split-view route integration for Orders, Products, Leads, and Customers;
- desktop `EntitySidePanel` non-modal behavior;
- mobile Drawer fallback;
- generic Drawer modal behavior;
- explicit five-card balanced summary usage;
- unified App Shell header structure.

## Viewport and browser QA status

Authenticated browser QA across the required viewport matrix is still pending in this container because no authenticated browser session/workspace credentials are available here.

Required manual matrix remains:

- Desktop: 1280×800, 1366×768, 1440×900, 1536×1024, 1920×1080.
- Tablet/mobile: 1024×768, 768×1024, 430×932, 390×844, 375×812.
- Themes: light and dark.

Manual QA must verify no horizontal body scroll, balanced Orders KPI layout, right-side entity panels, mobile Drawer fallback, shell header alignment, and readable dual-theme surfaces.
