# Sprint 8A.1 — Staging Access, Runtime Compatibility & E2E Gate Execution

## 1. Scope

Sprint 8A.1 attempted to close the Sprint 8A execution gaps by reusing the existing staging release-gate runner and documentation framework. It did not add features, roles, billing, password reset, email invitations, Meta Ads live sync, Nova Poshta TTN creation, database migrations, schema changes, or UI redesign.

## 2. Execution environment

The execution environment is still unable to reach the public staging URLs. Both the Vercel frontend and Render backend health preflight return the platform proxy error `CONNECT tunnel failed, response 403` before Sellora application code responds.

## 3. Secure inputs status

| Input group | Status | Notes |
| --- | --- | --- |
| `STAGING_FRONTEND_URL` / `STAGING_API_URL` | DEFAULTED | Runner used the documented staging URLs because no overriding environment values were present. |
| OWNER credentials | MISSING | `STAGING_OWNER_EMAIL` / `STAGING_OWNER_PASSWORD` were not present. |
| MANAGER credentials | MISSING | `STAGING_MANAGER_EMAIL` / `STAGING_MANAGER_PASSWORD` were not present. |
| ANALYST credentials | MISSING | `STAGING_ANALYST_EMAIL` / `STAGING_ANALYST_PASSWORD` were not present. |
| QA workspace ID | MISSING | `STAGING_TEST_WORKSPACE_ID` was not present. |
| Controlled-write flag | TESTED | `STAGING_ALLOW_CONTROLLED_WRITES=true` was tested, but writes were blocked before mutation because G0/G1/workspace resolution did not pass. |

No passwords, tokens, authorization headers, full workspace IDs, database URLs, provider keys, or real user emails were committed.

## 4. Release manifest

| Component | Branch | Commit/deployment | Runtime URL | Result |
| --- | --- | --- | --- | --- |
| Frontend | UNKNOWN — evidence unavailable | UNKNOWN — evidence unavailable | `https://sellora-web-staging.vercel.app/` | BLOCKED by proxy 403. |
| Backend | UNKNOWN — evidence unavailable | UNKNOWN — evidence unavailable | `https://sellora-api-staging.onrender.com` | BLOCKED by proxy 403. |
| Database | n/a | Expected revision `202607080020` | Runtime revision unavailable | BLOCKED; no runtime compatibility proof. |

## 5. Network/deployment result

| Target | Result | HTTP status | Duration | Notes |
| --- | --- | ---: | --- | --- |
| Frontend `/` | FAIL | 0 | not trusted as app timing | Proxy returned `CONNECT tunnel failed, response 403`; not a Sellora app response. |
| Frontend `/login` | BLOCKED | n/a | n/a | Not opened because the frontend origin itself was unreachable. |
| Backend `/health` | FAIL | 0 | not trusted as app timing | Proxy returned `CONNECT tunnel failed, response 403`; not a Sellora API response. |

## 6. Runtime Alembic result

Repository static head remains `202607080020`. Runtime Alembic revision could not be verified by SQL console, protected shell command, or diagnostic endpoint in this environment. No `alembic upgrade` was executed.

Result: **BLOCKED**.

## 7. Read-only smoke result

Command attempted:

```bash
python scripts/staging_release_gate.py --mode read-only
```

Result: **BLOCKED / RED**.

The runner emitted a sanitized artifact with `run_id` prefix `8A1-`, frontend/backend status `FAIL`, database compatibility `BLOCKED`, all roles `BLOCKED`, and no token/password output.

## 8. OWNER result

**BLOCKED.** OWNER credentials were unavailable, so login, `/auth/me`, QA workspace membership, dashboard, settings, team page and OWNER-only action smoke could not execute.

## 9. MANAGER result

**BLOCKED.** MANAGER credentials were unavailable, so operational route access and admin-denial checks could not execute.

## 10. ANALYST result

**BLOCKED.** ANALYST credentials were unavailable, so read-route access and direct mutation denial checks could not execute.

## 11. Workspace switching result

**BLOCKED.** No authenticated QA workspace session was available. Workspace A/B switching, delayed-response isolation, detail-panel closure and rapid A → B → A checks could not execute.

## 12. Controlled-write E2E result

Command attempted with the required safety flag:

```bash
STAGING_ALLOW_CONTROLLED_WRITES=true python scripts/staging_release_gate.py --mode controlled-write
```

Result: **BLOCKED before writes**. The runner did not create or mutate business data because staging access, credentials and QA workspace resolution did not pass.

## 13. Cross-workspace negative result

**BLOCKED.** Runtime cross-workspace negative checks for order/customer/variant/shipment/update and request-body `workspace_id` override could not execute on staging. Local automated workspace-injection tests from Sprint 7E.1 remain the only automated proof available in this environment.

## 14. Browser/mobile result

**BLOCKED.** Browser QA could not open staging. Desktop 1366px and mobile 375px, 390px, 430px and 768px checks were not performed.

## 15. Console/network result

**BLOCKED.** Browser console, Network, Application storage and cookie/session inspection could not execute. The only network evidence is the staging proxy 403 before app/API response.

## 16. Cleanup result

No cleanup was required because no synthetic Lead, Customer, Product, Variant, Inventory transaction, Order, Payment/status transition, Shipment draft or dashboard-affecting record was created.

## 17. Issues found

| ID | Severity | Gate | Issue | Status |
| --- | --- | --- | --- | --- |
| 8A-QA-001 | Critical | G0 | Frontend staging unreachable from this environment by proxy 403. | Open |
| 8A-QA-003 | Critical | G0 | Backend `/health` unreachable from this environment by proxy 403. | Open |
| 8A-QA-004 | Major | G1 | OWNER/MANAGER/ANALYST credentials missing. | Blocked |
| 8A1-QA-001 | Major | Runtime | Runtime Alembic revision unavailable. | Blocked |
| 8A1-QA-002 | Major | G6 | Controlled-write E2E flow not executed. | Blocked |
| 8A1-QA-003 | Major | G10/G11 | Browser/mobile/console QA not executed. | Blocked |

No app-level cross-workspace leak, unauthorized mutation, data corruption, secret exposure, or order/inventory corruption was observed because staging could not be reached.

## 18. Fixes implemented

- Extended `scripts/staging_release_gate.py` to emit `8A1-` run IDs and include the 8A.1 artifact fields required for runtime revision, role status, core E2E status, workspace switching, browser/mobile, console/network and cleanup status.
- Added `frontend/scripts/staging-e2e-closure-regression.mjs` to require Sprint 8A.1 evidence without replacing real staging execution.
- Updated Sprint 8A docs, issue log, pilot decision, MVP readiness, known limitations and README while preserving original Sprint 8A blocked evidence.

No product feature, migration, Meta Ads external write, Nova Poshta external write, role change or schema change was implemented.

## 19. Remaining blockers

- Execution environment still cannot reach Vercel/Render staging URLs.
- Secure synthetic OWNER/MANAGER/ANALYST credentials are unavailable.
- Dedicated QA workspace ID is unavailable.
- Runtime Alembic revision is unknown.
- Read-only smoke cannot pass until G0/G1 are unblocked.
- Controlled-write E2E cannot safely execute until staging access, credentials and QA workspace are available.
- Browser/mobile QA cannot execute until staging is reachable.

## 20. Sprint status

**Sprint 8A.1 — BLOCKED ⚠️**

Preparing scripts and docs does not complete Sprint 8A.1. Real staging evidence is still unavailable.

## 21. Release decision

**RED — NO-GO**

Do not provide staging access to pilot shops. The release remains blocked because staging availability, role authentication, runtime database compatibility, controlled-write E2E and browser/mobile QA are not verified.
