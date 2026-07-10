# Sprint Dd.1 Component Inventory

## Frontend architecture audit

- App uses Next.js App Router under `frontend/src/app` with protected pages wrapped by `AppShell` in the root layout.
- Shared shell components live in `frontend/src/components`: `app-shell`, `app-sidebar`, `app-topbar`, workspace/profile menus, feedback dialog, pagination, filters, and existing dialog helpers.
- Existing UI state primitives live in `frontend/src/components/ui/states.tsx`; Sprint Dd.1 extends this area with shared design-system primitives and overlay foundations.
- Localization dictionaries live in `frontend/src/i18n/messages/uk.json` and `frontend/src/i18n/messages/en.json`; UI copy should continue to go through `useI18n` where components render feature-specific text.
- Auth, workspace restore, switching, and membership state are exposed through `frontend/src/hooks/use-auth.ts` and `frontend/src/stores/auth.store.tsx`.
- Styling uses Tailwind CSS with semantic CSS variables in `frontend/src/app/globals.css` and Tailwind configured in `frontend/tailwind.config.ts`.

## Existing components found

| Area | Existing component(s) | Sprint Dd.1 decision |
| --- | --- | --- |
| App shell | `AppShell`, `AppSidebar`, `AppTopbar` | Refactor in place to the dark SaaS shell; preserve routes, auth, workspace logic, mobile drawer and bottom nav. |
| Brand | `BrandIcon`, `BrandLockup` | Reuse unchanged inside sidebar/topbar. |
| Buttons/actions | Local page buttons, topbar buttons, dialog buttons | Add shared `Button` and `IconButton`; migrate shell actions where safe and keep page handlers unchanged. |
| Inputs/selects/forms | Local feature forms | Add shared `FormField`, `Input`, `Select`, `Textarea`, `Checkbox` as the foundation for future page sprints. |
| Dialogs | `FormDialog`, `ConfirmActionDialog`, `BottomSheet`, `MobileMoreSheet` | Add shared `Drawer`, `Modal`, and `ConfirmationDialog` overlay foundation with focus management for future migration. |
| Tables | Feature tables in leads/orders/products/customers/etc. | Add shared `DataTable` foundation; defer page-level table redesigns to later Epic Dd sprints. |
| Pagination | `PaginationControls` | Keep existing component; add design-system `Pagination` primitive for new standardized tables. |
| States | `LoadingSkeleton`, `EmptyState`, `ErrorState` | Refactor visual styling to semantic dark tokens. |
| Badges | Feature status badges | Add shared `StatusBadge`; feature-specific enum mappings remain UI-level and unchanged. |
| Filters | `filter-controls`, date range selectors | Add `FilterBar`/toolbar primitive; preserve existing feature filtering behavior. |

## Components to refactor in place later

- Feature tables should gradually adopt `DataTable` without replacing mobile cards.
- Feature forms should migrate to `FormField` and shared controls without changing API payloads.
- Existing `FormDialog` and feature drawers can migrate to the shared `Drawer` foundation where workflows require side panels.

## Sprint Dd.3 additions

| Area | Component(s) | Decision |
| --- | --- | --- |
| CRM protected pages | `WorkspacePage`, `WorkspaceHeader`, `MetricCard`, `CompactSummary` | Shared wrappers for Dashboard, Leads, and Customers; avoid page-local duplicated headers and KPI cards. |
| Entity details | `EntityDrawer`, `FieldGrid`, `FieldItem`, `DrawerTabs` | Shared drawer/detail foundations for Lead and Customer detail flows using existing overlay behavior. |

## Sprint Dd.4.2 additions

- `WorkspaceSplitView` — shared protected-page split layout for list/table content plus a desktop entity side panel.
- `EntitySidePanel` — responsive entity details surface: non-modal desktop `<aside>` and modal mobile Drawer sheet.
- `CompactSummary` now includes count-aware balanced layouts for five-card KPI/summary rows.
