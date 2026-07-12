# Sprint 8A — Staging Release Gate & End-to-End Smoke QA

## 1. Scope

Sprint 8A is a release-gate and smoke-QA sprint. It adds a reproducible staging smoke runner, documents the staging gate evidence, and records a pilot release decision without adding product features, database migrations, Meta Ads writes, Nova Poshta carrier actions, billing, invitations, or RBAC role changes.

## 2. Environment

| Area | Value | Verification status |
| --- | --- | --- |
| Frontend staging URL | `https://sellora-web-staging.vercel.app/` | BLOCKED in this container by proxy `CONNECT tunnel failed, response 403`. |
| Backend staging URL | `https://sellora-api-staging.onrender.com` | BLOCKED in this container by proxy `CONNECT tunnel failed, response 403`. |
| Credentials | Expected through `STAGING_*` environment variables only | BLOCKED: OWNER, MANAGER and ANALYST credentials were not present in the local validation environment. |
| Database | Staging PostgreSQL/Supabase only | BLOCKED: runtime revision was not safely available; Sprint 7F remains blocked. |

## 3. Release manifest

| Component | Branch | Commit SHA | Deployment timestamp | URL | Status |
| --- | --- | --- | --- | --- | --- |
| Frontend | unknown from local container | unknown | unknown | `https://sellora-web-staging.vercel.app/` | BLOCKED: public network path returned proxy 403 before app response. |
| Backend | unknown from local container | unknown | unknown | `https://sellora-api-staging.onrender.com` | BLOCKED: public network path returned proxy 403 before `/health` response. |
| Database | n/a | expected Alembic head `202607080020` | n/a | not recorded | BLOCKED: runtime revision not verified. |

The repository Alembic static inspection remains separate from runtime migration QA. Sprint 8A does not execute runtime migrations.

## 4. Test-data policy

The smoke runner supports the required `E2E-8A-<timestamp>` synthetic-data prefix for future controlled-write runs, but the executed local run stayed read-only because no staging credentials or explicit `STAGING_ALLOW_CONTROLLED_WRITES=true` flag were available. No real customer, order, address, phone, credential, API key, Meta Ads write, or Nova Poshta shipment was used.

## 5. Gate G0 result — Deployment

**Status: BLOCKED / RED evidence.**

- Frontend preflight attempted against the staging URL and failed before application response with proxy `CONNECT tunnel failed, response 403`.
- Backend health preflight attempted against `/health` and failed before application response with proxy `CONNECT tunnel failed, response 403`.
- HTTPS URLs are documented, but the local container cannot reach them.
- Frontend/backend deployment commits could not be identified from the blocked local network path.

## 6. Gate G1 result — Authentication/session

**Status: BLOCKED.**

OWNER, MANAGER and ANALYST staging credentials were not present in the environment. Login, `/auth/me`, workspace persistence, logout, browser Back behavior, and invalid-credential UX could not be truthfully validated.

## 7. Gate G2 result — Workspace/team

**Status: BLOCKED.**

Workspace switching, Workspace Settings, Team page, last-OWNER protections, and role restrictions require authenticated staging access and could not be executed.

## 8. Gate G3 result — Dashboard

**Status: BLOCKED.**

Dashboard route smoke, KPI state verification, period visibility, workspace switch refresh, and missing-data display could not be executed without authenticated staging access.

## 9. Gate G4 result — Leads/customers

**Status: BLOCKED.**

Lead and customer list/detail/create/edit/archive smoke could not be executed. No synthetic lead or customer was created.

## 10. Gate G5 result — Products/inventory

**Status: BLOCKED.**

Product, variant, inventory record, and controlled stock-in smoke could not be executed. No synthetic product, variant, or inventory transaction was created.

## 11. Gate G6 result — Orders

**Status: BLOCKED.**

The core synthetic order flow could not be executed. This is release-blocking for pilot readiness until a reachable staging environment and safe QA credentials are available.

## 12. Gate G7 result — Shipments

**Status: BLOCKED.**

Shipment route smoke could not be executed. No manual/draft shipment and no real Nova Poshta action was attempted.

## 13. Gate G8 result — Finance/advertising/analytics/import

**Status: BLOCKED.**

Routes could not be opened in staging. Deeper Import, Finance and Advertising validation remains assigned to later Phase 8 sprints and was not pulled into Sprint 8A.

## 14. Gate G9 result — Settings/integrations

**Status: BLOCKED.**

Settings, Workspace Settings, Team, Import Settings, Integrations, Nova Poshta status and Meta Ads status could not be validated in staging.

## 15. Gate G10 result — Mobile/PWA

**Status: BLOCKED.**

Mobile viewport and PWA browser smoke could not be executed because staging app access was blocked from this container. Local static PWA/mobile regressions were run separately.

## 16. Gate G11 result — Network/console/errors

**Status: BLOCKED.**

Browser console and Network panel review could not be executed. The only runtime network evidence collected here is the proxy 403 blocking the staging frontend/backend connection.

## 17. OWNER result

**Status: BLOCKED.** OWNER credentials were not available through `STAGING_OWNER_EMAIL` / `STAGING_OWNER_PASSWORD`.

## 18. MANAGER result

**Status: BLOCKED.** MANAGER credentials were not available through `STAGING_MANAGER_EMAIL` / `STAGING_MANAGER_PASSWORD`.

## 19. ANALYST result

**Status: BLOCKED.** ANALYST credentials were not available through `STAGING_ANALYST_EMAIL` / `STAGING_ANALYST_PASSWORD`.

## 20. Mobile result

**Status: BLOCKED.** Manual browser/mobile evidence for 375×812, 390×844, 430×932, 768×1024 and 1366×768 could not be collected from the blocked staging path.

## 21. Security regression result

Local security and regression validation was executed to ensure Sprint 8A did not introduce tenant/RBAC regressions, migrations, Meta feature scope, credentials, or real customer/order data. The new staging-release regression guard validates documentation completeness and the blocked release decision.

## 22. Defects found

See `docs/staging-release-issues.md`.

## 23. Fixes implemented

- Added `scripts/staging_release_gate.py`, a safe staging release-gate runner that reads URLs/credentials from environment variables, masks tokens/passwords, writes a sanitized artifact, supports read-only and guarded controlled-write modes, and exits non-zero for must-pass failures.
- Added `frontend/scripts/staging-release-gate-regression.mjs` to ensure Sprint 8A evidence remains present and honest.
- Added release-gate documentation and updated readiness/known-limitation docs.

No product feature, schema migration, Meta Ads write, Nova Poshta shipment, or RBAC change was implemented.

## 24. Remaining limitations

- Staging frontend/backend access is blocked from this container by proxy 403.
- OWNER/MANAGER/ANALYST staging credentials were unavailable.
- Runtime database revision was not verified; Sprint 7F remains blocked.
- Controlled synthetic write E2E flow was not executed.
- Browser/mobile/manual QA screenshots were not collected.
- Nova Poshta real validation, Import deep QA, Finance deep QA and Advertising deep QA remain assigned to later Phase 8 sprints.

## 25. Sprint status

**Sprint 8A — BLOCKED ⚠️**

The gate was prepared and attempted, but required staging evidence could not be collected because the staging URLs were unreachable from this container and credentials were unavailable.

## 26. Release decision

**RED — NO-GO**

Do not show this staging deployment to controlled pilot shops yet. The release is not rejected due to a confirmed Sellora app defect; it is blocked because staging availability, authentication, role coverage, core E2E order flow, mobile/browser QA and runtime database compatibility could not be verified.
