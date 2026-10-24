# Direct order evidence + Raspberry live-source integration — 2026-10-24

**State: QA-only / no deployment.** Integrates the runtime parity from PR #328
with the Direct → TTN → Order evidence feature from PR #327.

## Conflict resolution
Two paths required a manual, non-destructive merge:
- `backend/app/api/v1/direct.py`: retained the live manually-confirmed
  `lead/ensure` manager operation AND both evidence preview / confirmation
  routes from PR #327.
- `backend/tests/security/test_endpoint_inventory.py`: combined expected
  route counts (242 total, 136 mutation, 212 workspace-scoped, 9 public)
  rather than replacing either set of routes.

## Tests completed
- Source compilation and Git diff whitespace validation: PASS.
- No-network disposable Docker backend test suite:
  **619 passed, 19 skipped, 0 failed**.
- Meta Instagram, Direct app-shell, mobile inbox and compact chat regression:
  PASS.
- Nova Poshta real-validation / historic status static tests: PASS.
- Independent, synthetic PostgreSQL 17 migration canary, 045→046:
  PASS (12 columns, RLS, uniqueness).
- Full GitHub Actions CI for combined branch: pending.

## Hard blockers
Do not deploy or apply the historical TTN bulk backfill on live data until
verified owner/manager/analyst browser E2E, source parity image checksum
comparison, immutable rollback image, encrypted database backup/restore
readiness, and coordinated frontend/backend cutover are all green. Do not
conflate exact tracking link with delivered/paid/profit status.

PR #329 is an integration QA artifact and does not close #264 or #326.
