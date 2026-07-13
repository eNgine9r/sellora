# Sellora MVP Readiness

## Current readiness decision

**READY FOR CONTROLLED GUIDED PILOT ✅**

This status is based on the completed Sprint 8A / 8A.1 staging release gate. It applies to the verified staging build and the tested MVP scope, not to unrestricted production launch or unvalidated external integrations.

## Core product readiness

| Area | Status | Notes |
|---|---|---|
| Leads and customers | Pilot-ready | Login, route access, workspace isolation and synthetic flow passed. |
| Products and variants | Pilot-ready | Product/variant creation and workspace scoping passed. |
| Inventory | Pilot-ready with known follow-up | Stock-in and order reservation passed; issue #134 tracks a zero-stock archived-row visibility edge case. |
| Orders | Pilot-ready | Creation, reservation, payment/status transitions, status history and profit/revenue state passed. |
| Shipments | Pilot-ready for draft workflow | Shipment draft passed; no real Nova Poshta action was executed. |
| Dashboard | Pilot-ready | Browser/mobile route and synthetic visibility checks passed. |
| Finance | Pilot-ready for tested MVP flow | Synthetic order/payment visibility passed. |
| Advertising | Pilot-ready for manual data review | Route/browser smoke passed; live Meta Ads sync is inactive. |
| Analytics | Pilot-ready | Route/browser smoke passed across all required viewports. |
| Settings and Team | Pilot-ready | OWNER access and responsive browser checks passed. |
| Localization | Pilot-ready | Ukrainian remains primary; no blocking mixed-language finding was recorded in the final gate. |
| Mobile UX | Pilot-ready | Required 375, 390, 430 and 768 widths passed. |
| Desktop UX | Pilot-ready | 1366 × 768 passed. |

## Sprint 8A.1 release evidence

### Runtime

- frontend available at the staging Vercel URL;
- backend `/health` returned HTTP 200;
- Render deployment reached `Application startup complete`;
- Alembic runtime revision and packaged head both equal `202607130021`;
- migration packaging is checked during Docker build and backend startup.

### Read-only gate

- OWNER, MANAGER and ANALYST login passed;
- `/auth/me` passed for all tested roles;
- QA workspace resolution passed;
- 13/13 core GET routes passed;
- console and artifact sanitization passed.

### Controlled-write gate

The complete synthetic flow passed:

```text
Lead → Customer → Product → Variant → Stock-in → Order
→ Payment/status → Shipment draft → Dashboard/Finance visibility
```

Tenant isolation, order reservation, status history, revenue/profit state and cleanup were verified.

### Browser/mobile gate

- 75/75 scenario checks passed;
- 0 failures;
- 0 warnings;
- 0 refresh-token loops;
- 0 core 404/500 findings;
- 0 CORS findings;
- 0 stale workspace-data findings;
- 0 password/token/API-key leaks.

Viewport matrix:

- 1366 × 768;
- 375 × 812;
- 390 × 844;
- 430 × 932;
- 768 × 1024.

## Pilot boundaries

The guided pilot may use:

- leads and customers;
- products, variants and inventory;
- orders, payments, statuses and profit;
- draft shipments;
- dashboard, finance and analytics;
- manual advertising metrics;
- settings, team and workspace switching;
- sanitized import data under guidance.

The guided pilot must not assume availability of:

- Instagram Direct API ingestion;
- Meta Ads live OAuth or automatic synchronization;
- Nova Poshta real TTN production behavior;
- billing/subscriptions;
- unrestricted public self-service onboarding;
- advanced AI/predictive features.

## Open non-blocking follow-ups

1. Resolve issue #134 for archived variant / zero-stock inventory-row visibility.
2. Complete dedicated Nova Poshta real-credential staging validation before relying on real TTN operations.
3. Complete deep advertising CSV import validation separately from route/browser smoke.
4. Continue audit-log standardization.
5. Validate PWA installation on real iOS and Android devices.
6. Add billing and broader onboarding only after pilot feedback validates product value.

## Release status

```text
Sprint 8A: APPROVED
Sprint 8A.1: APPROVED
MVP readiness: CONTROLLED PILOT READY
Release decision: GREEN
```

## Next readiness phase

Proceed to controlled pilot onboarding, observation, feedback collection and defect triage. Do not recreate Sprint 8A.1 unless a deployment, migration, authentication, tenant-isolation or core E2E regression requires the same gate to be rerun.