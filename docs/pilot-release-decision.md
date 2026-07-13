# Pilot Release Decision — Sprint 8A / 8A.1

## Decision

**GREEN — GO FOR CONTROLLED PILOT ✅**

Sellora staging may be opened to a limited, guided pilot cohort under the documented product and integration limitations.

## Evidence supporting the decision

- frontend staging is available;
- backend `/health` returns HTTP 200;
- runtime Alembic revision and packaged head match at `202607130021`;
- OWNER, MANAGER and ANALYST authentication passed;
- `/auth/me` and QA workspace resolution passed;
- read-only gate passed all required core GET routes;
- controlled-write E2E passed in an isolated synthetic workspace;
- order reservation, payment/status history, revenue/profit state and draft shipment behavior passed;
- cross-workspace references were rejected;
- Nova Poshta provider endpoints were not called;
- browser/mobile matrix passed 75/75 checks across five required viewport sizes;
- console/network checks found no runtime exception, refresh loop, core 404/500, CORS failure or token/password/API-key exposure;
- synthetic QA data was cleaned up.

## Allowed pilot scope

- limited invited shops;
- guided onboarding and support;
- CRM leads/customers;
- products, variants and inventory;
- orders, payments, statuses and profit visibility;
- shipment drafts without assuming real Nova Poshta provider validation;
- manual advertising metrics;
- dashboard, finance and analytics review;
- synthetic or sanitized import testing under guidance.

## Not approved by this decision

- unrestricted public production launch;
- live Instagram Direct ingestion;
- Meta Ads live OAuth or automatic sync;
- real Nova Poshta TTN creation without its dedicated validation;
- billing/subscription collection;
- unrestricted self-service onboarding;
- use of unsanitized real customer exports for QA.

## Pilot operating rules

1. Keep the pilot cohort controlled and identifiable.
2. Use workspace isolation and role assignments exactly as tested.
3. Do not store secrets in feedback, screenshots or issue comments.
4. Treat external-provider actions as unavailable until separately approved.
5. Monitor issue #134 and any new pilot regressions.
6. Retain rollback and staging-first deployment discipline.

## Release status

```text
Sprint 8A: APPROVED
Sprint 8A.1: APPROVED
Release decision: GREEN
Target: controlled guided pilot
```

The next phase may proceed with pilot onboarding and observation rather than recreating Sprint 8A.1 scope.