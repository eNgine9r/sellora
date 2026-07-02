# Sprint 4.5.1 — Advertising Staging QA, Runtime Validation & Pilot Readiness Check

Date: 2026-07-01

## Decision

**Advertising module blocked for pilot ⚠️** until the required staging/runtime inputs are available and the runtime QA checklist is completed with synthetic data only.

This document does not claim pilot readiness and does not mark Sprint 4.4 fully approved.

## Required staging/runtime inputs

The following required inputs were not available in this environment:

- staging frontend URL;
- staging backend URL;
- secure test credentials provided outside the report;
- controlled QA workspace;
- OWNER or MANAGER test role confirmation;
- permission confirmation to create synthetic campaigns, leads, customers, orders, and import test data;
- safe PostgreSQL test/staging DB access;
- migration window approval;
- rollback/backup confirmation.

Because these inputs were missing, staging/browser/runtime validation was not executed and was not faked.

## Local validation baseline

Repository baseline:

- `git status` returned a clean working tree before Sprint 4.5.1 documentation changes.
- `git log --oneline -5` showed the latest Sprint 4.5 commit on the current branch.
- `frontend/package-lock.json` exists and remains the npm lockfile source of truth.

Frontend validation:

- `npm --prefix frontend ci` passed.
- `npm --prefix frontend run typecheck` passed.
- `npm --prefix frontend run build` passed.

Backend validation:

- `python -m pip install -r backend/requirements.txt` passed.
- `python -m compileall backend/app backend/tests` passed.
- `cd backend && python -m pytest` passed with `154 passed, 1 warning`.
- `cd backend && python -c "from app.main import app; print('app import ok')"` passed.

Regression scripts:

- `node frontend/scripts/advertising-attribution-mvp-regression.mjs` passed.
- `node frontend/scripts/advertising-insights-decision-support-regression.mjs` passed.
- `node frontend/scripts/advertising-import-attribution-reporting-regression.mjs` passed.
- `node frontend/scripts/advertising-staging-pilot-readiness-regression.mjs` passed.
- `node frontend/scripts/advertising-reporting-consolidation-regression.mjs` passed.
- `node frontend/scripts/localization-regression.mjs` passed.

## PostgreSQL migration runtime QA

Status: **BLOCKED**.

The Sprint 4.4 migration `backend/alembic/versions/202607010015_manual_ad_attribution.py` was not run with `alembic upgrade head`, `alembic downgrade -1`, and `alembic upgrade head` because no safe PostgreSQL test/staging DB access, migration window approval, or rollback/backup confirmation was available.

Do not run this validation against production. The migration remains runtime-unvalidated until a safe DB is provided.

## Advertising CSV import staging QA

Status: **BLOCKED**.

The `/settings/import` and `/advertising` browser flow was not executed because no staging frontend/backend URL, secure credentials, controlled QA workspace, or permission to create synthetic import data was available.

Advertising import remains **not pilot-ready** until manual staging import QA passes with the existing synthetic CSV template.

## Browser QA

Status: **BLOCKED**.

The following browser checks were not executed and must remain open:

- `/advertising` reporting structure and formula QA;
- campaign insights QA with GOOD / WATCH / PROBLEM / NO_DATA scenarios;
- `/leads` attribution create/edit/remove flows;
- `/orders` attribution create/edit/remove flows;
- order detail attribution display;
- workspace/cross-workspace browser or manual API rejection checks.

Backend tests and regression scripts continue to provide local coverage, but they do not replace staging browser QA.

## Mobile and theme QA

Status: **BLOCKED**.

The following widths/pages still need runtime review:

- 375px, 390px, 768px, and desktop widths;
- `/advertising`, `/leads`, `/orders`, order detail, and `/settings/import`;
- light mode, dark mode if available, and dark-sidebar/light-content readability.

No screenshots were captured because no safe staging/browser session was available.

## Safety and privacy

Safety scans were run locally. Matches were limited to safe existing placeholders, package registry URLs in `frontend/package-lock.json`, synthetic test values, privacy documentation, and expected auth/config symbol names.

No real credentials, tokens, API keys, database URLs, workspace IDs, cookies, session data, Meta tokens, Nova Poshta keys, real customer data, real ad account data, `.env` files, screenshots with secrets, or private logs were added.

## Remaining blockers

- Required staging/runtime inputs are missing.
- PostgreSQL Alembic upgrade/downgrade/upgrade remains runtime-unvalidated.
- Advertising CSV import staging QA remains pending.
- `/advertising` browser QA remains pending.
- Campaign insights browser QA remains pending.
- Lead/order/order-detail attribution browser QA remains pending.
- Workspace/cross-workspace runtime QA remains pending.
- Mobile/theme QA remains pending.
- Advertising import remains not pilot-ready.
- Sprint 4.4 remains conditionally approved until PostgreSQL runtime and staging/browser QA pass.

## Confirmations

- Backend/API enum values were not changed.
- Auth/session/workspace behavior was not changed.
- Product/order/inventory/import/analytics/feedback/Nova Poshta/advertising flows were not changed in code during Sprint 4.5.1.
- Deployment architecture was not changed.
- Meta Ads API, automatic Meta sync, automatic attribution, Instagram Direct API, AI Direct parser, click tracking, and multi-touch attribution were not implemented.
- Advertising import was not marked pilot-ready.
- Sprint 4.4 was not marked fully approved.
