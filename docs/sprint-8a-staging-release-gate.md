# Sprint 8A — Staging Release Gate & End-to-End Smoke QA

## Final gate status

**APPROVED ✅**

Sprint 8A and its 8A.1 closure reused the existing staging release-gate implementation. No new product scope was introduced.

## Environment

| Area | Value | Status |
|---|---|---|
| Frontend | `https://sellora-web-staging.vercel.app/` | PASS |
| Backend | `https://sellora-api-staging.onrender.com` | PASS |
| Backend health | `/health` | HTTP 200 |
| Database | Supabase staging PostgreSQL | PASS |
| Alembic runtime/head | `202607130021` | PASS |
| Synthetic roles | OWNER / MANAGER / ANALYST | PASS |
| QA workspace | `Sellora QA — Sprint 8A.1` | PASS |

## Gate summary

| Gate | Area | Result |
|---|---|---|
| G0 | Deployment | PASS |
| G1 | Authentication/session | PASS |
| G2 | Workspace/team | PASS |
| G3 | Dashboard | PASS |
| G4 | Leads/customers | PASS |
| G5 | Products/inventory | PASS |
| G6 | Orders | PASS |
| G7 | Shipments | PASS |
| G8 | Finance/advertising/analytics/import route smoke | PASS |
| G9 | Settings/integrations route smoke | PASS |
| G10 | Browser/mobile | PASS |
| G11 | Console/network/errors | PASS |

## Read-only execution

The read-only gate verified frontend/backend availability, role authentication, `/auth/me`, workspace resolution, 13 core GET routes, database compatibility and artifact sanitization.

Result: **PASS**.

## Controlled-write execution

The isolated synthetic flow completed:

```text
Lead → Customer → Product → Variant → Stock-in → Order
→ Payment/status → Shipment draft → Dashboard/Finance visibility
```

Verified reservation, status history, profit/revenue state, draft-only shipment behavior, tenant isolation and cleanup. No Nova Poshta provider endpoint was called.

Result: **PASS**.

## Browser/mobile execution

Tested:

- 1366 × 768;
- 375 × 812;
- 390 × 844;
- 430 × 932;
- 768 × 1024.

Result: **75/75 checks PASS**, with 0 runtime exceptions, 0 refresh loops, 0 core 404/500 responses, 0 CORS errors, 0 stale workspace-data findings and 0 credential/token/API-key leaks.

Final browser run: `29241616449`.

## Deployment incident resolved during closure

Render temporarily failed because its running image could not locate Alembic revision `202607130021`. The repository migration was correct; image packaging/runtime diagnostics were added. The successful deployment confirmed the packaged head and runtime revision are both `202607130021` before starting Uvicorn.

## Remaining non-blocking limitations

- real Nova Poshta TTN creation is not covered by this gate;
- Meta Ads live OAuth/sync remains inactive;
- deep advertising CSV import QA remains separate from route smoke;
- deep Import Center data-set validation remains separate;
- issue #134 tracks zero-stock inventory visibility after variant archive;
- billing and unrestricted self-service onboarding are not included.

## Sprint status

**Sprint 8A — APPROVED ✅**

## Release decision

**GREEN — GO FOR CONTROLLED PILOT**

The decision applies to the verified staging build and guided pilot use. It is not approval for unrestricted production access or unvalidated external-provider actions.