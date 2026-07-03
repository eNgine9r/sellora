# Sprint 6B Risk Closure QA Report

## Status

**Overall result: CONDITIONALLY APPROVED ⚠️**

This report records what was actually validated for Sprint 6B risk closure and what remains blocked by missing external access or production-level prerequisites.

## Scope

Sprint 6B is limited to encrypted token storage foundation, Meta connection records, and live OAuth backend foundation. It must not be treated as production-ready Meta sync.

Confirmed repository context:

- `meta_ad_connections` migration exists as revision `202607030018`.
- `meta_ad_connections` is workspace-scoped.
- Stored token material is server-side only.
- Meta Ads API sync is not active.
- Live sync, scheduled jobs, apply-sync, Conversions API, customer/order transfer to Meta, and production-ready OAuth are not implemented.

## 1. PostgreSQL runtime migration QA — 202607030018_meta_ad_connections

### Repository review

Migration file reviewed:

`backend/alembic/versions/202607030018_meta_ad_connections.py`

Expected migration behavior:

- Creates `meta_ad_connections` table.
- Adds workspace scope through `workspace_id`.
- Adds soft-delete fields.
- Adds token-related fields without raw token response columns.
- Adds indexes for workspace, status, external ad account ID, and workspace/status lookup.
- Downgrade drops indexes and table.

### Staging runtime result

**Status: Pending / not fully closed ⚠️**

Reason: direct PostgreSQL connection, Supabase/Render migration console, or controlled staging DB access was not available in this execution context. Therefore, I could not run:

- `alembic upgrade 202607030018`
- `alembic downgrade 202607020017`
- row-count/checksum verification
- DB performance query checks
- rollback restore test

### Required closure steps

Before production approval, run on staging DB:

```bash
cd backend
alembic current
alembic upgrade 202607030018
alembic current
alembic downgrade 202607020017
alembic upgrade head
```

Then verify:

```sql
SELECT to_regclass('public.meta_ad_connections');
SELECT indexname FROM pg_indexes WHERE tablename = 'meta_ad_connections';
SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name = 'meta_ad_connections';
```

### Rollback requirement

Do not mark this risk fully closed until a staging rollback is tested against a real backup or disposable staging DB clone.

## 2. Real staging OAuth validation

### Repository/UI review

Staging UI reviewed at:

`https://sellora-web-staging.vercel.app/settings/integrations`

Observed:

- Meta Ads card is visible.
- Status is `Не активний`.
- Current source remains `Ручне внесення / CSV-імпорт`.
- UI says real Meta account is not connected.
- The future action button is disabled/copy-only: `Підключити Meta Ads — скоро`.

### Result

**Status: Pending / intentionally not production-ready ⚠️**

Reason: real Meta Developer App credentials, callback URLs, and approved permissions are not available. The staging UI also correctly keeps the real connection unavailable.

### Safety result

The UI behaves safely for the current sprint:

- no real Meta redirect is exposed from the UI;
- no live Meta account is connected;
- manual/CSV advertising source remains active;
- sync is not represented as active.

### Required closure steps

To fully close real OAuth validation later:

1. Add Meta Developer App staging OAuth redirect URL.
2. Enable only staging environment variables.
3. Start OAuth as OWNER.
4. Validate state mismatch rejection.
5. Validate token exchange with test account.
6. Validate revoke + reconnect.
7. Confirm tokens are never returned to frontend.
8. Confirm disconnect clears encrypted token material.

## 3. Legal review

### Staging UI review

Login page footer exposes legal links:

- Privacy Policy
- Terms
- Data Deletion

This is good for Meta readiness, but legal review itself cannot be fully completed by QA without a qualified legal reviewer.

### Result

**Status: Pending ⚠️**

Reason: QA can verify the presence of legal pages/links, but cannot certify legal compliance.

### Required closure steps

- Qualified legal review of Privacy Policy.
- Qualified legal review of Terms.
- Qualified legal review of Data Deletion flow/page.
- Confirm public production URLs are stable and accessible.
- Confirm Meta App settings use the same URLs.

## 4. Meta Developer App setup

### Staging UI review

Meta connection is not active and is intentionally future-gated. This is correct for Sprint 6B.

### Result

**Status: Pending ⚠️**

Reason: no access to Meta Developer dashboard was available during this execution.

### Required closure steps

- Create/confirm Business type Meta Developer App.
- Add app icon, category, Privacy URL, Terms URL, Data Deletion URL.
- Add staging OAuth redirect URL.
- Add required products/permissions only after legal/staging readiness.
- Prepare App Review screencast.
- Do not request live production permissions until staging flow is validated.

## 5. Safe non-production workspace validation

### Staging UI review

Logged into staging successfully with a test account.

Validated synthetic flows:

- Created lead: `Тестовий лід`.
- Opened lead edit dialog and verified editable fields.
- Created customer: `Тестовий клієнт` with synthetic phone.
- Created product: `Тестовий товар` with SKU `TEST001`.
- Checked Orders, Products, Inventory, Shipments, Advertising, Finance, Reports, Calendar, Notes, Insights, Settings.

### Result

**Status: Partially validated ✅/⚠️**

Validated: staging UI, authentication, and basic non-production data creation.

Not validated: database-level isolation queries, direct workspace ID filtering at SQL level, and RBAC with MANAGER/ANALYST test accounts.

### Required closure steps

- Run backend workspace isolation tests with direct API/DB access.
- Validate OWNER/MANAGER/ANALYST accounts separately.
- Remove or archive synthetic test data after QA.

## 6. Browser/mobile staging QA

### Desktop browser QA

Environment:

- Browser: Chromium
- Staging URL: `https://sellora-web-staging.vercel.app/`

Validated:

- Public landing loads.
- Login page loads.
- Authenticated private routes load.
- Sidebar navigation works.
- Main modules do not hard-crash in desktop Chromium.
- Loading skeletons appear on async pages.

### Mobile QA

**Status: Pending ⚠️**

Reason: no full mobile device/browser matrix was executed in this pass. Desktop Chromium only was used.

### Required closure steps

Test at mobile width:

- `/login`
- `/dashboard`
- `/leads`
- `/customers`
- `/orders`
- `/products`
- `/inventory`
- `/shipments`
- `/advertising`
- `/finance`
- `/analytics`
- `/settings/import`
- `/settings/integrations`

Required checks:

- no body-level horizontal overflow;
- sidebar drawer opens and closes cleanly;
- dialogs fit phone screens;
- table/card layouts remain usable;
- calendar/date inputs do not disappear in dark mode;
- primary buttons remain touch-friendly.

## Risk table

| Risk | Result |
|---|---|
| PostgreSQL runtime migration QA for `202607030018_meta_ad_connections` | Pending ⚠️ |
| Real staging OAuth validation | Pending ⚠️ |
| Legal review | Pending ⚠️ |
| Meta Developer App setup | Pending ⚠️ |
| Safe non-production workspace validation | Partially validated ✅/⚠️ |
| Browser/mobile staging QA | Desktop partial; mobile pending ⚠️ |

## Final decision

Sprint 6B should remain:

**CONDITIONALLY APPROVED ⚠️**

It is safe as a gated foundation, but not safe to mark as production-ready, pilot-ready, or live Meta sync-ready.

## Follow-up recommendation

Create a focused follow-up sprint:

**Sprint 6B.1 — Staging Runtime Validation & Meta OAuth Readiness Closure**

Scope:

- run real PostgreSQL migration/rollback QA;
- validate feature gates in staging environment variables;
- finish legal URL readiness;
- configure Meta Developer App in staging only;
- run real OAuth sandbox/tester flow;
- complete mobile staging QA;
- archive QA-created synthetic records.
