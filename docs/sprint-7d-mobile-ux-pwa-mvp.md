# Sprint 7D — Mobile UX / PWA MVP

## 1. Scope

Sprint 7D focused on frontend mobile UX and a safe PWA MVP foundation. No backend module, Meta feature, offline CRM sync, push notification feature, service worker, or database migration was added.

## 2. Mobile audit

Audit covered the app shell, topbar, mobile More sheet, profile/workspace menus, Dashboard, Leads, Orders, Customers, Products, Inventory, Shipments, Advertising, Finance, shared dialogs, current manifest, layout metadata, and public icons.

Findings addressed:

- Mobile navigation needed a persistent quick path between core modules.
- Leads, Orders, and Customers still relied on horizontal table scroll for important mobile workflows.
- PWA manifest existed but needed owner-facing app metadata and safer install values.
- Shared form dialogs needed localized close copy and explicit mobile sheet markers.

## 3. App shell changes

The protected app shell now includes a mobile bottom quick navigation for Dashboard, Leads, Orders, Products, and Finance. It keeps the existing sidebar drawer and mobile More bottom sheet intact.

The main content gets bottom padding on mobile so bottom navigation does not cover page CTAs. The sidebar drawer has an explicit dialog role and translated close label.

## 4. Mobile navigation result

Mobile navigation result: improved.

- Sidebar remains the complete navigation drawer.
- Bottom quick nav provides thumb-friendly access to the main operational loop.
- Active route state is visible.
- Workspace/profile controls remain available through the existing profile/mobile More sheet.

## 5. Tables-to-cards result

Leads, Orders, and Customers now render mobile cards below the medium breakpoint while preserving desktop tables.

Product, Inventory, Shipment, and Dashboard recent-order cards already had mobile card layouts and were preserved.

## 6. Forms/modals/sheets result

Shared `FormDialog` keeps a viewport-limited scrollable panel and now uses localized close copy. It also carries a mobile form sheet marker for regression coverage.

Follow-up: a dedicated full-screen form shell for the most complex order creation flow could further improve small-screen keyboard behavior.

## 7. Mobile dashboard result

Sprint 7C Dashboard sections already stack responsively. Sprint 7D keeps the Dashboard readable with bottom-nav-safe spacing and does not introduce chart overflow changes.

## 8. Mobile core flow result

The mobile review flow is improved for:

```text
Dashboard → Leads → Orders → Customers → Products / Inventory → Shipments → Finance / Advertising
```

Users can navigate the core review path from the bottom nav and drawer, inspect cards for leads/orders/customers, and keep More/profile/workspace actions reachable.

## 9. PWA manifest result

PWA manifest now uses owner-facing metadata:

- app name: Sellora — CRM для Instagram-магазинів;
- short name: Sellora;
- standalone display mode;
- start URL: `/dashboard`;
- theme color: `#111827`;
- background color: `#ffffff`;
- existing Sellora SVG icon configured as maskable.

Layout metadata keeps manifest, viewport, Apple web app support, icons, and theme color configured.

## 10. Service worker/cache policy

Service worker/offline support is intentionally deferred.

Reason: Sellora contains private workspace business data. This sprint does not cache API responses, private HTML pages, tokens, customer records, order records, finance data, advertising data, or workspace data.

Acceptable Sprint 7D PWA MVP outcome: manifest + icons + mobile metadata + app-like responsive behavior, with offline CRM data sync deferred until a safe caching strategy exists.

## 11. Accessibility notes

- Mobile drawer has dialog semantics and a backdrop close action.
- Bottom navigation has an aria label and active route state.
- Existing More bottom sheet and profile overlays remain reachable.
- Card actions use comfortable touch-height buttons.

## 12. Breakpoint QA notes

Static responsive review covered required targets:

- 375px;
- 390px;
- 430px;
- 768px;
- 1366px desktop regression.

Manual browser/device QA remains recommended for PWA install prompts and iOS/Android home-screen behavior.

## 13. RBAC/workspace safety

No backend permissions, workspace dependencies, API clients, repositories, services, or routes were changed.

Existing `X-Workspace-ID`, workspace switching, OWNER/MANAGER/ANALYST behavior, and mobile More/profile workspace controls remain unchanged.

## 14. Known limitations

- Service worker and offline support are deferred to avoid caching sensitive business data.
- PWA install testing is limited in this environment because a real mobile browser/home-screen install flow is not available.
- The create-order flow can still be improved with a dedicated mobile full-screen wizard in a future sprint.
- Sprint 7F runtime PostgreSQL migration QA remains blocked and separate.
- No database migration was added in Sprint 7D.

## 15. Final recommendation

**Sprint 7D — CONDITIONALLY APPROVED ⚠️**

Reason: mobile navigation, mobile cards for key workflows, mobile dialog polish, PWA manifest metadata, docs, and regression coverage were improved without backend or migration changes. Full approval should wait for manual device/browser QA of mobile breakpoints and PWA install behavior.
