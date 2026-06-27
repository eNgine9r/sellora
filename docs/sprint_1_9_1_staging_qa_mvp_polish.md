# Sprint 1.9.1 – Staging QA & MVP Polish

Sprint 1.9.1 focuses on frontend polish without changing backend contracts or deployment architecture.

## Completed UX scope

- Root `/` is now a public dark SaaS landing page for Sellora instead of a login redirect.
- `/login` is polished, uses Sellora branding, and redirects authenticated users to `/dashboard`.
- `/dashboard` is the primary private dashboard route with KPI cards, charts, recent orders, top products, notifications, quick actions, and activity feed.
- The authenticated shell now uses dedicated sidebar and topbar components with desktop fixed navigation and mobile drawer navigation.
- Required private routes are present: dashboard, leads, customers, orders, products, inventory, shipments, advertising, finance, reports, and settings.
- Brand PNG assets live under `frontend/public/brand/` and are used for logo/icon and favicon metadata.

## Guardrails

- Backend logic and API contracts were not rewritten.
- Existing auth/session refresh flow remains in place.
- No manual token or workspace input was added to the normal user flow.
- No deployment architecture changes were made.
