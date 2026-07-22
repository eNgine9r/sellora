# Sprint 17 — Mobile architecture decision

Status: **APPROVED FOR PROOF OF CONCEPT**. A public store release remains gated.

## Decision

Sellora will keep the current Next.js application as the web product and use Expo Router for a dedicated iOS/Android client. The mobile client reuses the existing FastAPI API and backend enums; it does not embed the web application and does not duplicate business rules.

The repository contains `mobile-poc/`, an Expo Go compatible proof of concept with:

- Expo Router navigation;
- FastAPI `/health` compatibility probe;
- 20-second request timeout;
- bearer authentication and `X-Workspace-ID` propagation;
- access, refresh, and workspace values stored in `expo-secure-store`;
- TanStack Query with an offline-first read cache.

## Boundaries

- The backend remains the source of truth for RBAC, workspace isolation, fulfillment, inventory, finance, and integrations.
- Tokens must never use AsyncStorage. Logout removes all SecureStore entries and query cache.
- A workspace switch must clear tenant-scoped queries before the new workspace is persisted.
- Offline support is read-cache only in the first release. Order, inventory, payment, shipment, and Direct writes require connectivity.
- Push notifications may carry opaque IDs only; message text and customer delivery data are fetched after authentication.
- Camera/media upload, background Direct sync, and native shipment-label printing are future scope.

## PWA versus native

| Criterion | PWA | Expo native |
| --- | --- | --- |
| Fastest release | Strong | Medium |
| App Store / Play Store presence | Weak | Strong |
| Reliable push and badges | Limited on iOS | Strong |
| Secure token storage | Browser-managed | SecureStore |
| Camera/media roadmap | Limited | Strong |
| Reuse of current UI | High | Low |
| Recommended role | Web fallback | Primary mobile direction |

Decision: continue improving the responsive web/PWA experience while building the operational mobile client with Expo.

## Delivery estimate

Assuming the existing API contracts remain stable:

1. Foundation, auth, workspace switching, design tokens: 2 weeks.
2. Direct inbox and notifications: 2–3 weeks.
3. Customers, orders, fulfillment, inventory: 3–4 weeks.
4. Store hardening, accessibility, privacy manifests, TestFlight/internal testing: 2 weeks.

Estimated controlled beta: **9–11 engineering weeks**. Public release requires the Sprint 15 pilot exit gate and separate Apple/Google review evidence.

## Store release plan

1. Register final bundle/package IDs and legal URLs.
2. Configure EAS development, preview, and production profiles.
3. Add privacy manifests, data-safety declarations, account deletion, and support contact.
4. Validate iOS and Android push credentials without secrets in the repository.
5. Run device QA, TestFlight, and Google Play internal testing.
6. Release gradually with crash monitoring and server-side feature gates.
