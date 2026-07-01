# Sprint 4.4.1 — Attribution Migration, Backend Validation & Browser QA Recovery

Date: 2026-07-01

## Result

Sprint 4.4 remains **CONDITIONALLY APPROVED ⚠️**.

The repository now contains the missing additive manual attribution migration and code paths for nullable lead/order campaign attribution, with backend service validation and frontend selectors/display. Automated backend app import, compile, frontend dependency recovery, typecheck, and production build were recovered. Full Alembic upgrade/downgrade and browser/mobile QA remain blocked by this non-interactive environment because the configured PostgreSQL host is unavailable and no browser/staging session credentials were provided in-repo.

## Migration validation

- Added `202607010015_manual_ad_attribution.py`.
- The migration is additive only:
  - `leads.campaign_id` nullable.
  - `orders.campaign_id` nullable.
  - indexes on both new columns.
  - foreign keys point to `ad_campaigns.id`.
  - `ON DELETE SET NULL` is configured for both relationships.
  - downgrade drops only the attribution foreign keys, indexes, and columns.
- Command attempted: `cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head`.
- Blocker: local Alembic validation could not connect to the configured PostgreSQL host `postgres` (`Temporary failure in name resolution`). No production or staging database was touched.

## Backend validation

- `LeadService` validates optional `campaign_id` through the workspace-scoped campaign repository before create/update.
- `OrderService` validates optional `campaign_id` through the workspace-scoped campaign repository before create/update.
- `campaign_id = null` remains valid for existing and new leads/orders.
- Missing, soft-deleted, or cross-workspace campaigns are rejected because `AdCampaignRepository.get(workspace_id, campaign_id)` filters by workspace and `deleted_at is null`.
- Order item replacement, profit recalculation, inventory reservation/transactions, payment status, and shipment behavior were not redesigned or bypassed.

## Frontend validation

- `npm install --package-lock-only` generated a real npm lockfile using registry access.
- `npm --prefix frontend ci` passed.
- `npm --prefix frontend run typecheck` passed.
- `npm --prefix frontend run build` passed.
- Lead and order forms now send nullable/optional `campaign_id` safely.
- Lead/order tables and order details show a campaign name when linked and `—` when unlinked.
- Campaign selector options show campaign name and platform instead of raw UUID-only UX.

## Browser and mobile/theme QA

Browser QA was not executed in this environment because no running frontend/backend browser session and no safe synthetic staging credentials were available. Required manual follow-up:

- `/leads`: create/edit with and without campaign, empty campaign selector, table display, runtime translation check.
- `/orders`: create/edit/change/remove campaign, totals/profit/inventory/shipment regression.
- `/advertising`: manual attribution summary period and workspace checks.
- 375px, 390px, 768px, desktop widths in light mode and dark mode if available.

## Remaining blockers

- Real/test DB Alembic upgrade/downgrade validation remains blocked until a reachable local PostgreSQL test database is available.
- Browser/mobile/theme QA remains blocked until a runnable environment with synthetic data is available.
- Advertising import remains not pilot-ready until manual staging import QA passes.

---

# Sprint 4.4.2 — PostgreSQL Migration Runtime QA, Browser Attribution QA & Analytics Test Fix

Date: 2026-07-01

## Result

Sprint 4.4 remains **CONDITIONALLY APPROVED ⚠️**.

Sprint 4.4.2 fixed the remaining July 1 backend analytics test fragility and recovered the full backend test suite. PostgreSQL runtime migration validation and browser/mobile/theme QA are still environment-blocked in this container because Docker/PostgreSQL/browser QA tooling is unavailable. No production or staging database was touched.

## PostgreSQL test DB result

- Existing project pattern is `docker-compose.yml` with PostgreSQL 16.
- `docker` / `docker compose` are not installed in this container.
- `psql`, `pg_isready`, and a local PostgreSQL server on `localhost:5432` are unavailable.
- Therefore, `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` could not be run against PostgreSQL here.
- Required follow-up: run the Alembic sequence against a safe local/CI PostgreSQL test database before final Sprint 4.4 approval.

## Alembic migration runtime result

Runtime validation remains blocked by missing PostgreSQL runtime tooling in this environment. Static migration review remains valid: the migration is additive, nullable, indexed, uses `ON DELETE SET NULL`, and downgrade removes only the Sprint 4.4 attribution artifacts.

## Full backend pytest result

- The previous July 1 failure was isolated to a test-data assumption in `test_dashboard_endpoint_payload`, not a production analytics formula bug.
- The test now uses a deterministic in-month dashboard date fixture so month-to-date assertions do not depend on the actual system date being the first day of a month.
- Full backend pytest now passes: `154 passed, 1 warning`.

## Frontend and attribution QA result

- `npm --prefix frontend ci` passed.
- `npm --prefix frontend run typecheck` passed.
- `npm --prefix frontend run build` passed.
- Lead edit attribution no longer requires raw campaign UUID entry; the edit dialog uses workspace campaign options with campaign name and platform labels.
- Browser/mobile/theme QA remains blocked because no runnable browser/staging session with synthetic credentials is available in this environment.

## Workspace/RBAC validation

Server-side cross-workspace protection remains enforced by backend services through workspace-scoped campaign lookup. Browser two-workspace QA was not possible here and should be completed in staging with synthetic data.

## Advertising import status

Advertising import remains **not pilot-ready** until manual staging import QA passes with synthetic data only.
