# Advertising 4.x Freeze and Part 5 Handoff

Sprint 4.14 freezes Advertising 4.x feature scope.

Final Advertising 4.x status: **Advertising 4.x — architecture-ready / locally validated / feature-frozen / not pilot-ready**.

Meta Ads status: **Meta Ads API — mock/future-ready / not active**.

Active Advertising data source: **manual entry / CSV import**.

## Freeze rules

Advertising is feature-frozen for now.

Allowed after freeze:

- critical bug fixes;
- safety fixes;
- documentation fixes;
- blocker QA execution when environment becomes available;
- small copy/localization corrections.

Not allowed after freeze:

- new Advertising features;
- live Meta OAuth;
- token storage;
- apply-sync;
- production sync jobs;
- Conversions API;
- new attribution models;
- automatic sync;
- financial formula changes without Part 5 scope;
- pilot-ready claims before blocker registry resolution.

## Advertising 4.x inventory

| Item | Status | Source of validation | Remaining limitation | Can be used in Part 5 finance formulas? |
|---|---|---|---|---|
| Manual advertising metrics entry | Implemented / feature-frozen | Backend tests, frontend build, advertising regressions | Runtime/browser QA still pending | Yes, as manual ad spend |
| CSV advertising import | Implemented / feature-frozen | Import docs, templates, regression scripts | Staging import QA pending (B-ADV-003) | Use with caution |
| Advertising KPI cards | Implemented / feature-frozen | Frontend build, reporting regressions | Browser/mobile/theme QA pending | Yes, as display context only |
| ROAS / ROI / CPA / CPL | Implemented / feature-frozen | Backend tests, metrics docs, regressions | Depends on manual/CSV source quality | Yes, with manual/CSV source label |
| Campaign insights: GOOD / WATCH / PROBLEM / NO_DATA | Implemented as display/status logic | Regressions and docs | Advisory only; no new persisted backend enum values | Use with caution; advisory only |
| Campaign comparison | Implemented / feature-frozen | Frontend build and regressions | Browser QA pending | Use for context, not accounting truth |
| Manual campaign attribution for leads/orders | Implemented / feature-frozen | Backend services/tests and frontend build | Staging/browser attribution QA pending (B-ADV-002) | Use with caution when `campaign_id` exists |
| Attributed revenue/profit summary | Implemented / feature-frozen | Analytics/reporting tests and docs | Attribution QA pending | Use with caution |
| Meta Ads readiness docs | Implemented / feature-frozen | Docs regressions | Live Meta not active | No direct formula dependency |
| Fake Meta Ads client | Implemented / feature-frozen | Backend unit tests | Synthetic only | No, test/demo only |
| Dry-run simulation | Implemented / feature-frozen | Backend unit tests | No DB writes/apply-sync | No direct Finance dependency |
| Read-only sync preview | Implemented / feature-frozen | Backend preview tests | No apply-sync/live API | No direct Finance dependency |
| External identity migration draft | Implemented / runtime-gated | Static migration tests | PostgreSQL runtime QA pending (B-ADV-006) | No until runtime QA and live sync future work |
| Sync persistence contract | Documented / feature-frozen | Technical docs | No persistence table for Meta sync runs in this sprint | No |
| Meta Ads not-active UX | Implemented / feature-frozen | Frontend build and UX regressions | Browser/mobile/theme QA pending | No |
| Mock OAuth service shell | Implemented / feature-frozen | Backend OAuth mock tests | Mock only; no production connection | No |
| Mock OAuth API boundary | Implemented / feature-frozen | Backend route tests and regression script | Disabled by default; mock only | No |
| OWNER-only mock route contract | Implemented / feature-frozen | Route-level RBAC tests | Mock only | No |
| Audit event stubs | Implemented / feature-frozen | Route tests and docs | Non-persistent only | No |

## Readiness matrix

| Area | Implemented | Local tests | Frontend build | Backend tests | Regression scripts | Browser QA | Runtime DB QA | Staging QA | Pilot-ready | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Manual metrics | Yes | Yes | Yes | Yes | Yes | Pending | N/A | Pending | No | Architecture-ready / locally validated |
| CSV import | Yes | Yes | Yes | Yes | Yes | Pending | N/A | Pending | No | Conditional until B-ADV-003 |
| Campaign insights | Yes | Yes | Yes | Yes | Yes | Pending | N/A | Pending | No | Advisory only |
| Manual attribution | Yes | Yes | Yes | Yes | Yes | Pending | Pending | Pending | No | Conditional until B-ADV-001/B-ADV-002 |
| Advertising reporting | Yes | Yes | Yes | Yes | Yes | Pending | N/A | Pending | No | Locally validated |
| Meta fake client | Yes | Yes | N/A | Yes | Yes | N/A | N/A | N/A | No | Synthetic/test-only |
| Sync preview | Yes | Yes | N/A | Yes | Yes | N/A | N/A | N/A | No | Read-only/no writes |
| External identity migration | Yes | Static only | N/A | Static tests | Yes | N/A | Pending | Pending | No | Runtime-gated |
| Mock OAuth shell | Yes | Yes | Copy only | Yes | Yes | Pending | N/A | Pending | No | Mock/future-ready |
| Mock API boundary | Yes | Yes | N/A | Yes | Yes | N/A | N/A | N/A | No | Mock/future-ready / disabled by default |

Overall:

- Architecture-ready ✅
- Locally validated ✅
- Runtime/staging validated ⚠️ Partial / pending
- Pilot-ready ❌ No

## Known blocker registry

The formal blocker registry lives in `docs/advertising-known-blockers.md` and tracks B-ADV-001 through B-ADV-010. Runtime/staging blockers are tracked separately and must not be marked passed without execution.

## Part 5 handoff

The Finance Part 5 handoff lives in `docs/finance-part-5-handoff.md`.

Part 5 may use Advertising data only as a **conditional manual/CSV source**. Live OAuth/token storage/apply-sync are future work. Finance must not depend on live Meta sync, automatic attribution, or unresolved Advertising runtime/staging QA.
