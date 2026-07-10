# Sellora Public Page Patterns

## Public layout

Use shared public components from `frontend/src/components/public-layout.tsx` for public marketing/auth pages:

- `PublicPageContainer`
- `PublicHeader`
- `PublicFooter`
- `PublicSection`
- `MarketingCTA`
- `IntegrationStatusBadge`

Public pages must use the Sprint Dd.1 semantic design tokens: dark canvas, dark elevated surfaces, subtle borders, purple primary, and the brand gradient only for primary marketing CTAs.

## Navigation and CTAs

- Header navigation should link only to real page sections or existing routes.
- Primary CTA must use a real available flow. For Sprint Dd.2 this is `/login` because registration, forgot password, and beta request routes do not exist.
- Do not add dead “start free”, fake trial, pricing, testimonial, or customer-logo blocks.

## Marketing sections

Landing pages should be concise and workflow-oriented:

1. Hero with a clear Instagram-shop value proposition.
2. Product preview marked as demo when values are illustrative.
3. Workflow section that maps Instagram request → lead → customer → order → payment/shipment/profit/repeat sale.
4. Capability cards with one concise benefit per module.
5. Integration status cards using truthful labels only.
6. One final CTA that repeats the real primary route.

## Integration status rules

Allowed labels:

- Доступно / Available
- Пілот / Pilot
- Beta
- Незабаром / Coming soon
- Не підключено / Not connected

Never present Instagram Direct, Meta Ads, or Nova Poshta as live unless the current product flow supports it.

## Auth page pattern

Login pages should:

- reuse the existing auth handler and redirect behavior;
- never prefill real credentials;
- use `autocomplete="email"` and `autocomplete="current-password"`;
- provide show/hide password;
- show general invalid-credentials copy;
- avoid staging credentials, JWT, RBAC, workspace IDs, or internal environment details.

## Responsive behavior

- Desktop: full navigation, two-column hero, split login layout.
- Tablet: navigation can simplify; layouts should stack without compression.
- Mobile: one-column landing, accessible menu overlay, full-width login form, wrapping legal links, and no horizontal body scroll.

## Accessibility

- Use semantic `header`, `nav`, `main`, `section`, and `footer`.
- Keep one `h1` per page.
- Provide visible focus states for every interactive element.
- Icon-only buttons require `aria-label`.
- Mobile menus must close with Escape, trap focus while open, and return focus to the trigger.
- Auth errors must use `role="alert"` / `aria-live` and connect to fields through `aria-describedby` where relevant.

## Dual-theme requirement for Dd.3–Dd.7

Every new or modified page/component must support and be validated in both light and dark themes on desktop and mobile.

Public-page specifics:

- Desktop public header controls must be 40px tall with matching radius and alignment.
- Mobile public menu actions must be 44px tall or full-width with matching radius.
- Public primary CTAs must be real flows; if registration/beta is unavailable, use `/login` or an in-page section link.
- Demo previews on mobile should use simplified stacked content instead of shrinking a desktop dashboard into an unreadable card.
- Login pages must show the form before marketing/product context below 1024px.

## CRM workspace pattern — Sprint Dd.3

Dashboard, Leads, and Customers should use the shared CRM workspace pattern:

- `WorkspacePage` for protected-page spacing and `min-width: 0` containment.
- `WorkspaceHeader` for compact title, description, and right-aligned actions.
- `MetricCard` for dashboard KPIs with period context and unavailable states.
- `CompactSummary` for compact lead/customer summary counts.
- `EntityDrawer` for lead/customer details on desktop and full-screen mobile sheets through the shared drawer foundation.

Rules:

- Do not use marketing hero blocks inside protected CRM pages.
- Do not compute global totals or segment totals from only a paginated table page; use server summaries when available or mark unavailable. If a list endpoint currently returns an unpaginated array, document that contract and keep derived segment metrics unavailable unless they come from a workspace-level summary source.
- Preserve existing workspace-scoped query keys and handlers.
- Mobile CRM lists should remain cards; desktop tables should not replace Sprint Dm.1 mobile UX.
- Every new or modified CRM page/component must support and be validated in both light and dark themes on desktop and mobile.

## Orders and Products workspace pattern — Sprint Dd.4

Orders and Products should follow the same protected CRM workspace rhythm as Dashboard, Leads, and Customers:

- Compact `WorkspaceHeader` with only real supported actions.
- `CompactSummary` cards only from reliable current data sources; if pagination is introduced, move workspace totals to server summaries or mark unavailable.
- Tokenized `FilterBar` controls with consistent 40px desktop control height.
- Desktop tables with selected row state; mobile card lists remain the mobile experience.
- Right-side `EntityDrawer`/sheet for details, using honest unavailable states for missing API-backed sections such as product history.
- Dual-theme validation is required for every touched Orders/Products surface.

## Workspace closure rules — Sprint Dd.4.1

- `WorkspacePage` must use the available protected content width and must not recenter CRM pages into a narrow column that creates a large sidebar/content gutter.
- Summary/KPI grids should use balanced auto-fit behavior or deliberate column spans; never leave a single orphan card on a second row at common desktop widths.
- Protected entity details should use the shared right-side panel behavior. Desktop panels must avoid blur-heavy modal takeovers; mobile can continue to use a lightweight sheet pattern.
- Dense selector panels inside modals must use semantic input/surface tokens, bounded scroll height, compact option rows, and visible selected/hover/focus states in both themes.

## Embedded entity panels — Sprint Dd.4.2

- Entity detail views on protected CRM pages must use the responsive side-panel pattern: non-modal desktop aside, modal mobile sheet.
- Standard generic Drawer remains modal and must not be repurposed globally for embedded page details.
- Five-card summary rows must use the explicit balanced layout: 3 + 2 at medium desktop and five equal columns on wide desktop.
