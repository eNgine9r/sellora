# Finance Readiness — Epic Sprint 5C

Sellora Finance is operational profit analytics, not full accounting or tax reporting.

Overall status: **Finance 5.x — implementation-ready / locally validated / runtime migration QA pending**.

Advertising data remains a conditional manual/CSV source until runtime/staging blockers are resolved.

Meta Ads API is not active.

Finance adjustments migration has passed static Alembic chain validation, but PostgreSQL runtime migration QA remains pending until tested against a safe staging/test database.

## Readiness matrix

| Area | Implemented | Backend tests | Frontend build | Regression scripts | Browser QA | Runtime DB QA | Staging QA | Pilot-ready | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Finance summary | Yes | Yes | Yes | Yes | Pending | N/A | Pending | No | Locally validated |
| Finance adjustments | Yes | Yes | Yes | Yes | Pending | Pending | Pending | No | Runtime migration QA pending |
| Finance breakdown | Yes | Yes | Yes | Yes | Pending | N/A | Pending | No | Locally validated |
| Finance trends | Yes | Yes | Yes | Yes | Pending | N/A | Pending | No | Locally validated |
| Finance dashboard | Yes | Static/local build | Yes | Yes | Pending | N/A | Pending | No | Mobile-stabilized statically |
| Mobile UX | Stabilized | N/A | Yes | Static script | Pending | N/A | Pending | No | Browser QA pending |
| Auth/API boundary | Yes | Existing auth tests | Yes | Yes | Pending | N/A | Pending | No | Smoke-guarded |
| Migration runtime QA | Migration exists | Static contract | N/A | Static checks | N/A | Pending | Pending | No | Safe DB required |
| Browser QA | Not executed | N/A | Yes | Static only | Pending | N/A | Pending | No | Playwright/browser unavailable |
| Advertising dependency | Conditional manual/CSV | Guardrails | Yes | Yes | Pending | Pending blockers | Pending | No | Advertising not pilot-ready |
| Meta API dependency | None active | Guardrails | Yes | Yes | N/A | N/A | Future | No | Meta Ads API inactive |

## 5C stabilization notes

- Read endpoints remain read-only and workspace-scoped.
- Finance adjustment writes remain MANAGER/OWNER only; ANALYST remains read-only.
- Reversed date ranges return a safe validation error instead of an unhandled server error.
- Zero-denominator values remain unavailable so the UI renders `—`, not NaN or Infinity.
- Browser/mobile QA is still pending because no browser runtime was available in this environment; static regression checks are not a substitute for screenshot QA.

## Sprint 6A dependency note

Meta Ads API is not active.

Sprint 6A prepares setup, security, OAuth, token storage, and QA design only. No live OAuth, no token storage, no live API calls, and no production sync were implemented.

Finance 5.x remains locally validated with runtime migration QA and browser/mobile QA blockers tracked separately. Advertising data remains a conditional manual/CSV source until runtime/staging blockers are resolved.
