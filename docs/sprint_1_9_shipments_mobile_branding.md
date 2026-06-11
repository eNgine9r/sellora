# Sprint 1.9 – Shipments Engine, Mobile UX, and Branding

Sprint 1.9 adds manual shipment tracking before any Nova Poshta API integration.

## Scope

- Manual shipment records linked to workspace orders.
- Tracking number / TTN storage, carrier, lifecycle status, recipient and delivery location details.
- Shipment status actions that delegate order lifecycle changes to `OrderService` so inventory rules stay centralized.
- Workspace-scoped shipment APIs and role access: OWNER/MANAGER write, ANALYST read-only.
- Mobile-first `/shipments` UX with responsive cards, touch-friendly forms, and a collapsible authenticated navigation drawer.
- Sellora branding in the login page, app shell, metadata, and favicon/app icon.

## Explicit exclusions

- No Nova Poshta API integration.
- No automatic TTN creation.
- No Meta Ads API, Instagram Graph API, AI Insights, or messaging notifications.
- No changes to the staging deployment architecture.

## Import Center

The Import Center now supports shipment dry-run/mapping using aliases for order number, TTN, carrier, status, recipient, city, and warehouse. Tests and examples must continue to use synthetic data only.
