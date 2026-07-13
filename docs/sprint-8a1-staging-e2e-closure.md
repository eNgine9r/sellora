# Sprint 8A.1 — Staging Access, Runtime Compatibility & E2E Gate Execution

## Final status

**APPROVED ✅**

Sprint 8A.1 reused the existing staging release-gate scope. No new product specification was created for the closure run.

## Scope executed

- verified staging frontend and backend availability;
- supplied synthetic OWNER, MANAGER and ANALYST credentials through GitHub Actions secrets;
- used the dedicated `Sellora QA — Sprint 8A.1` workspace;
- verified runtime Alembic compatibility without manually running a migration during the runtime-revision check;
- executed read-only staging gate;
- executed controlled-write synthetic E2E flow;
- executed browser/mobile, console and network QA;
- cleaned or archived synthetic records;
- updated release and readiness documentation.

## Runtime manifest

| Component | Runtime | Result |
|---|---|---|
| Frontend | `https://sellora-web-staging.vercel.app/` | PASS |
| Backend | `https://sellora-api-staging.onrender.com` | PASS |
| Backend health | `/health` | HTTP 200 |
| PostgreSQL | Supabase staging | PASS |
| Alembic runtime revision | `202607130021` | PASS — matches packaged head |
| Backend deployment | Render commit `66f0da8f6d25bdbc40458c203ad2d5f200db5ba9` | PASS |

Render startup diagnostics confirmed:

```text
Alembic revision verified: 202607130021
Alembic packaged heads: 202607130021
Alembic current revision: 202607130021 (head)
Starting Sellora backend...
Application startup complete.
```

## Secure inputs

Credentials were supplied only through GitHub Actions repository secrets. Passwords, access tokens, refresh tokens, authorization headers and provider API keys were absent from reports and uploaded artifacts.

## Read-only gate

**PASS ✅**

Verified:

- frontend and backend health;
- OWNER, MANAGER and ANALYST login;
- `/auth/me` for all three roles;
- QA workspace resolution;
- 13/13 core GET routes;
- runtime database compatibility;
- sanitized console output and JSON artifact.

No controlled writes were performed during this run.

## Controlled-write E2E

**PASS ✅**

Synthetic flow:

```text
Lead
→ Customer
→ Product
→ Variant
→ Stock-in
→ Order
→ Payment/status
→ Shipment draft
→ Dashboard/Finance visibility
```

Verified:

- all entities remained scoped to the QA workspace;
- order reserved the expected product variant;
- revenue and profit states matched the synthetic inputs;
- order status history was created;
- shipment remained `DRAFT`;
- Nova Poshta provider endpoints were not called;
- cross-workspace references were rejected;
- cleanup completed.

The original blocker caused by global `order_number` uniqueness was fixed by migration `202607130021_workspace_scoped_order_numbers.py`. The active constraint is now workspace-scoped.

## Browser/mobile QA

**PASS ✅**

Viewport matrix:

- 1366 × 768;
- 375 × 812;
- 390 × 844;
- 430 × 932;
- 768 × 1024.

Result: **75/75 scenario checks PASS**, 0 failures, 0 warnings.

Covered Login, Dashboard, workspace switch, Leads, Customers, Products, Inventory, Orders, Shipment draft, Finance, Advertising, Analytics, Settings, Team and Logout.

Console/network result:

- runtime exceptions: 0;
- refresh-token loops: 0;
- core 404/500 responses: 0;
- CORS failures: 0;
- stale Workspace A data after switching to B: 0;
- password/token/API-key exposure: 0;
- body-level horizontal overflow: 0.

GitHub Actions run: `29241616449`.

## Cleanup

- active `QA-BROWSER-*` markers after cleanup: 0;
- controlled-write synthetic entities were archived or deleted as appropriate;
- temporary Browser Workspace B was deactivated;
- the primary Sprint 8A.1 QA workspace remains available for future regression runs;
- no real shop data was used.

## Follow-up issues

| Issue | Severity | Status | Release impact |
|---|---|---|---|
| #129 workspace-scoped order number uniqueness | Blocker | Resolved | None |
| Render image missing packaged Alembic revision | Critical deployment incident | Resolved by build/startup verification | None |
| #134 archived variant may leave a zero-stock inventory row visible | Minor/Major follow-up | Open | Does not block the controlled pilot |

## Release decision

**GREEN — GO FOR CONTROLLED PILOT ✅**

Sprint 8A.1 is closed. This approval covers the tested staging build and controlled pilot scope; it does not activate Meta Ads live sync, Nova Poshta real TTN creation, billing or unrestricted production onboarding.