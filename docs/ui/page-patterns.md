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
