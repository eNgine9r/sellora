# Sprint Dd.4.4 — Protected Shell, Spacing & Orders Layout Polish

## Scope

Frontend-only layout polish for the protected Sellora workspace. No backend, API contract, auth/session, RBAC, workspace isolation, query-key, business-rule, or calculation changes were made.

## Protected shell polish

- The desktop shell continues to use the unified two-row/two-column grid introduced in Dd.4.3.
- The brand cell and topbar now share the same `bg-canvas/92` header surface and `--topbar-height`, making the first row feel like one continuous full-width header.
- The topbar inner row now spans the full available width, and the search area is no longer capped by a desktop max-width that created an empty top-right zone.
- The brand cell stays compact and uses a subtle hover border instead of an oversized card treatment.
- Sidebar navigation now starts with a top padding offset below the header row so the menu no longer feels glued to the brand/topbar junction.

## Shared spacing polish

- `WorkspacePage` now uses slightly tighter default vertical spacing and gutters while preserving responsive breathing room.
- The change applies to protected workspace pages that use the shared wrapper, including Dashboard and Orders, without introducing page-local spacing hacks.

## Orders layout polish

- Orders still uses the explicit `CompactSummary layout="five-balanced"` summary so the fifth “Problematic” KPI does not become an accidental orphan.
- Orders flow now matches the list-page structure: header → five-card summary → filters → contextual daily summary → table/list → bottom pagination.
- The main orders pagination and page-size/result controls moved below the orders table/list.
- Order table, selected row, embedded right-side detail panel, create/edit modal, and archive confirmation behavior were preserved.

## Regression notes

- Desktop entity details remain embedded side panels through `WorkspaceSplitView`/`EntitySidePanel`.
- Mobile entity details still use the modal Drawer fallback.
- Generic Drawer behavior remains modal for forms, confirmations, and mobile overlays.
- Create Order selectors were not changed in this sprint.

## Manual QA still required

Authenticated browser QA is still required for:

- Desktop: 1280×800, 1366×768, 1440×900, 1536×1024, 1920×1080.
- Tablet/mobile: 1024×768, 768×1024, 430×932, 390×844, 375×812.
- Both light and dark themes.

Manual checks: full-width header, compact brand/topbar/sidebar junction, sidebar top spacing, no horizontal body scroll, Orders bottom pagination, balanced five-card KPI row, side-panel behavior, and mobile bottom nav/drawer preservation.
