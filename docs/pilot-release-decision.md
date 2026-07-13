# Pilot release decision

## Current decision

**GREEN — GO FOR CONTROLLED GUIDED PILOT ✅**

Controlled guided pilot is approved for staging-backed, closely monitored onboarding with synthetic or pilot-approved data, including the Sprint 8B first-run checklist and isolated demo workspace flow. Unrestricted public production launch is not approved.

## Approved deployment baseline

- Backend: Render commit `2c9fe282a99cb06b4d76239a09f1dc3c1672a112`.
- Frontend: Vercel commit `f61913cfb1850146a9dc66067274792280fb67de`.
- Runtime/package Alembic revision: `202607130021`.
- Sprint 8B staging closure: 181 PASS, 0 FAIL.
- Browser evidence: 91 screenshots across 5 viewport configurations in light and dark themes.
- Network evidence: 1,142 captured events, 0 core 500s, 0 external Meta/Nova Poshta requests and 0 credential exposure.

## Boundary

Allowed:
- guided OWNER/MANAGER/ANALYST pilot walkthroughs;
- synthetic QA workspaces;
- clearly labeled demo workspace data;
- controlled first-run validation and feedback collection;
- real ↔ demo workspace switching within approved pilot accounts;
- safe demo workspace deactivation by its OWNER.

Not allowed:
- public self-service signup;
- billing/subscriptions;
- live Meta/Instagram writes;
- real Nova Poshta TTN creation without explicit approval;
- production-data import without separate import hardening;
- unrestricted public production launch.

## Sprint 8B approval

**Sprint 8B — APPROVED ✅**

The following release conditions are confirmed:

- browser/mobile staging QA passed;
- demo eligibility uses immutable server-side audit provenance rather than name/slug heuristics;
- duplicate-click and runtime idempotency passed;
- rollback regression passed;
- real workspace remained unchanged;
- workspace switching produced zero stale/cross-workspace records;
- OWNER/MANAGER/ANALYST behavior passed;
- the core demo dataset scope is explicit and truthful;
- no Critical or Major Sprint 8B issue remains open.

Detailed evidence is recorded in `docs/sprint-8b-staging-closure.md`.

## Pilot status

```text
Existing controlled pilot baseline: GREEN ✅
Sprint 8B first-run/demo features: GREEN ✅
Controlled guided pilot: APPROVED ✅
Unrestricted public production launch: NOT APPROVED
```

## Next release path

Proceed to **Sprint 8C — Import Center Pilot Hardening**.
