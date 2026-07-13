# Staging Release Issues — Sprint 8A / 8A.1

## Final issue log

| ID | Severity | Gate | Issue | Resolution | Status |
|---|---|---|---|---|---|
| 8A-QA-001 | Critical | G0 | Frontend staging was unreachable from the original validation container. | Re-executed from GitHub Actions environment with working staging access; frontend returned HTTP 200 and browser matrix passed. | Resolved |
| 8A-QA-003 | Critical | G0 | Backend `/health` was unreachable from the original validation container. | Render deployment repaired; `/health` returned HTTP 200. | Resolved |
| 8A-QA-004 | Major | G1 | OWNER/MANAGER/ANALYST credentials were unavailable. | Synthetic credentials supplied through GitHub Actions repository secrets. | Resolved |
| 8A-QA-005 | Major | G6 | Synthetic core E2E order flow had not executed. | Controlled-write flow completed in isolated QA workspace. | Resolved |
| 8A-QA-006 | Major | Runtime | Runtime Alembic revision was not verified. | Supabase SQL and Render startup diagnostics confirmed `202607130021`. | Resolved |
| 8A1-QA-001 | Major | Runtime | Runtime Alembic compatibility unknown. | Runtime revision and packaged head both confirmed as `202607130021`. | Resolved |
| 8A1-QA-002 | Major | G6 | Controlled-write E2E blocked. | Full Lead → Customer → Product/Variant → Stock → Order → Shipment/Finance flow passed. | Resolved |
| 8A1-QA-003 | Major | G10/G11 | Browser/mobile/console QA blocked. | Final run completed 75/75 checks with 0 failures and 0 warnings. | Resolved |
| 8A1-QA-004 | Blocker | G6 | First order in second workspace failed because `order_number` had global uniqueness. | Issue #129 fixed by workspace-scoped unique constraint in migration `202607130021`. | Resolved |
| 8A1-QA-005 | Critical | Deployment | Render image could not locate revision `202607130021`. | Added image-build revision verification and startup diagnostics; deployment succeeded at commit `66f0da8`. | Resolved |
| 8A1-QA-006 | Follow-up | Inventory cleanup | Archived variant can leave a visible zero-stock inventory row. | Tracked as issue #134; synthetic stock was zeroed and final QA cleanup completed. | Open — non-blocking |

## Final release impact

No open Critical or Major issue blocks the controlled pilot release.

The only open item is issue #134, which concerns zero-stock inventory-row visibility after archive. It does not affect order reservation, revenue/profit correctness, tenant isolation, shipment draft behavior or the verified pilot flow.

## Security result

No password, access token, refresh token, authorization header, provider API key or real customer record was found in the sanitized staging artifacts.

## Decision

**GREEN — controlled pilot release allowed.**