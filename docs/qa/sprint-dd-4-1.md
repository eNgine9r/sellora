# Sprint Dd.4.1 QA — Dashboard & Workspace Detail UI Closure

## Implementation summary

- Tightened the shared CRM workspace layout so protected pages use the available content width from the sidebar instead of centering inside a narrow max-width container.
- Updated `CompactSummary` to use an auto-fit grid so Orders, Products, Dashboard, Leads, and Customers summary cards reflow into balanced rows and avoid orphan KPI tiles at common desktop widths.
- Changed the shared drawer overlay behavior so desktop detail views no longer use a blurred modal-style backdrop; panels now read as integrated right-side workspace panels while retaining the existing mobile sheet behavior and close/focus lifecycle.
- Retokenized the create-order product/category/variant selector surfaces to match Sellora controls: compact trigger height, semantic input border/background, compact product option rows, bounded scroll height, consistent selected/hover states, and theme-safe text.

## Screenshot/manual review issues addressed

- Extra content gutter: fixed globally through `WorkspacePage` by removing the centered `max-w-7xl` container in favor of a full-width workspace grid.
- KPI orphaning: fixed globally through `CompactSummary` auto-fit columns.
- Create Order dropdown styling: fixed selector panels and option rows in `OrderForm`.
- Detail overlays: removed desktop backdrop blur for the shared drawer used by Orders, Products, Leads, and Customers.

## Dashboard closure notes

- Dashboard already uses the protected workspace structure, compact header, KPI row, attention block, funnel, charts, advertising, stock, recent orders, notifications, and activity blocks from Dd.3.
- Dd.4.1 layout changes apply to Dashboard through the shared workspace wrapper and summary behavior without changing metrics or data contracts.
- No dashboard metric was invented or rederived from an unsafe source in this sprint.

## Business logic preserved

- No backend, database, API contract, auth/session, RBAC, workspace isolation, query key, order workflow, product inventory, Nova Poshta, Meta Ads, or finance formula changes were made.
- Existing create/edit/archive/status/detail handlers remain in place.

## Manual QA checklist

Manual authenticated browser QA remains required:

- Routes: `/dashboard`, `/orders`, `/products`, `/leads`, `/customers`.
- Themes: light and dark.
- Desktop: 1280×800, 1366×768, 1440×900, 1536×1024, 1920×1080.
- Tablet/mobile: 1024×768, 768×1024, 430×932, 390×844, 375×812.
- Verify no excessive sidebar/content gutter, no horizontal body scroll, balanced KPI rows, polished order selector panels, right-side detail panels without blur-heavy modal feel, selected row/card state, and preserved mobile cards/navigation.

## Automated validation

- `npm run typecheck` — passed.
- `npm run build` — passed with existing non-blocking warnings.
- `npm run lint` — passed with existing warnings outside Dd.4.1 scope.
- `node frontend/scripts/localization-regression.mjs` — passed.
- `node frontend/scripts/auth-api-boundary-regression.mjs` — passed.
- `node frontend/scripts/mobile-ux-pwa-mvp-regression.mjs` — passed.
- `git diff --check` — passed.

## Sprint status

CONDITIONALLY APPROVED until authenticated browser visual QA confirms the reviewed layout issues are closed.
