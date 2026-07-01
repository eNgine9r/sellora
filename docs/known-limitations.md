# Sellora Known Limitations for Pilot Users

Sellora is ready for guided MVP pilot testing, but the following limitations must be communicated honestly before users rely on it for daily operations.

## Not automated yet

- Instagram Direct API is not connected yet.
- Meta Ads API is not connected yet.
- Billing/subscriptions are not implemented yet.
- Advanced AI insights and predictive analytics are not implemented yet.
- AI Direct parser is not implemented yet.

## Integrations and imports

- Nova Poshta production TTN behavior may need final validation with real API settings.
- Some reports depend on imported or manually entered data.
- Import dry-run should be tested with copied/safe spreadsheet data before importing operational data.
- Feedback attachments/screenshots are not supported yet.

## Feedback/privacy boundaries

- Do not include passwords, API keys, tokens, private spreadsheets, raw customer lists, full authorization headers, or workspace IDs in feedback messages.
- Pilot feedback is workspace-scoped and intended for product triage, not for storing support evidence with sensitive data.

## Product scope

- Sellora currently focuses on CRM, products, inventory, orders, shipments, manual advertising metrics, imports and analytics.
- Full self-serve onboarding, billing, team administration and automated external API ingestion are planned after pilot validation.

## Sprint 3.0 Nova Poshta validation limitations

- Nova Poshta status sync is available as a manual action where a TTN exists, but automated background synchronization is not yet enabled.
- Nova Poshta TTN cancellation is not fully production-validated and should be treated as manual operational follow-up until a dedicated cancellation workflow is added.
- Sender counterparty and contact person refs may still need to be sourced from the shop’s Nova Poshta account; Sellora validates that they are present before TTN creation but does not yet browse all account sender entities.
- Production validation must use the staging checklist and a controlled test order because real TTN creation may create real records in the Nova Poshta account.

## Sprint 3.1 — Shipment / TTN limitations

- Printable or downloadable Nova Poshta TTN documents are not implemented yet. Pilot users should copy the TTN number from Sellora and use the Nova Poshta cabinet for printing.
- Delivery status sync depends on Nova Poshta API availability and requires an existing TTN; when unavailable, Sellora shows a safe localized message instead of raw third-party payloads.
- TTN creation does not automatically complete an order. Order status and shipment status are intentionally kept separate.

## Sprint 3.2 — Staging validation limitations

- Real Nova Poshta staging validation still requires a controlled shop-owned credential and may create records in the Nova Poshta account if TTN creation is executed.
- Automated tests continue to use mocked Nova Poshta clients; no real Nova Poshta API calls are made in CI/regression scripts.
- Printable/downloadable TTN documents remain out of scope; copy the TTN and use the Nova Poshta cabinet for document workflows.

## Sprint 3.2.1 — Remaining validation blockers

- Real Nova Poshta staging validation cannot be marked complete until a controlled shop-owned API key is provided and the manual checklist is executed in staging.
- Frontend lint is not configured for non-interactive CI yet; `next lint` opens the Next.js ESLint setup prompt.
- Dependency installation can still fail in environments where the Python/npm registry proxy returns `403 Forbidden`; CI should use an approved registry mirror or dependency cache.

## Sprint 4.0 — Advertising and Meta Ads limitations

- Automatic Meta Ads OAuth, token refresh, ad account selection and daily insights sync are not active yet.
- Campaign/adset/ad external ID mapping is documented for future additive schema work; current MVP campaign rows remain manual/import oriented.
- Manual advertising import is the supported pilot path and must not be mixed with fake Meta API data.
- Nova Poshta real-key staging validation remains a release blocker for enabling delivery workflow, but it does not block Sprint 4.0 advertising foundation work.

## Sprint 4.0.1 — Remaining advertising validation blockers

- Manual browser-based staging QA for `/advertising`, `/settings/integrations`, Dashboard, Analytics and Import Center still requires staging access and synthetic advertising data.
- `next lint` still uses the deprecated interactive Next.js setup flow; migrate to ESLint CLI configuration in a dedicated tooling task.
- npm still reports environment proxy config warnings; CI should keep using approved dependency caches or registry access to avoid another dependency-restore outage.

## Sprint 4.1 Advertising Limitations

- Manual browser-based staging QA still needs to be completed with synthetic advertising data before pilot approval.
- Real Meta Ads API sync is not active; the integration card is a readiness placeholder only.
- Campaign attribution is optional and not yet a full lead/order-to-campaign relation.
- Gross profit is documented as a business metric, but the current advertising import path focuses on spend, messages, leads, orders, revenue, and net profit unless a future schema explicitly adds gross-profit advertising fields.

## Sprint 4.2 Advertising Pilot Limitations

- The committed advertising templates are synthetic and safe for QA, but they do not prove a real store export will be clean; pilot stores must sanitize real business files before import.
- Browser-based staging QA with the CSV template still needs to be executed in the actual staging environment.
- Automatic Meta Ads sync, token refresh, ad account selection, and real campaign/ad attribution remain future work.

## Sprint 4.2.1 Validation Limitations

- The CSV template CI/build validation can pass locally, but browser-based staging import still requires deployed staging access and a synthetic QA workspace.
- The project still uses deprecated interactive `next lint`; lint should be migrated to an explicit ESLint CLI setup in a separate tooling task.
- Committed advertising templates must remain CSV-only; do not reintroduce binary `.xlsx` template files into tracked docs or public assets.

## Sprint 4.2.2 Manual Staging Blocker

- Manual browser staging QA for the advertising CSV import flow is still blocked until staging frontend/backend access, credentials, and a controlled QA workspace are provided.
- CSV dry-run, execute import, duplicate behavior, `/advertising`, Dashboard, Analytics, mobile, and theme checks are not approved from local validation alone.
- Advertising import should remain marked not pilot-ready until the deployed staging flow is completed with synthetic data.

## Sprint 4.2.3 Staging Access Limitation

- Staging QA remains blocked because the required staging frontend/backend URLs, secure credentials, controlled QA workspace, and role/permission confirmation were not provided.
- CSV template download, dry-run, execute import, duplicate import behavior, `/advertising`, Dashboard, Analytics, zero-denominator display, mobile, and theme checks remain unverified on deployed staging.
- Pilot readiness remains blocked until the deployed staging flow is completed with synthetic data only.

## Sprint 4.3 Advertising Insights Limitations

- Campaign insights are MVP decision support based on manual/CSV-imported aggregates for the selected period; they are not automated Meta recommendations.
- Decision statuses are frontend-computed and are not persisted backend enums.
- Top/weak campaign ranking depends on the quality and completeness of imported/manual metrics.
- Advertising import remains not pilot-ready while deployed staging QA is blocked.

## Sprint 4.3.1 Advertising Insights Validation Notes

- Decision statuses remain frontend-computed and non-persisted.
- NO_DATA campaigns are intended to appear in comparison only; they are not eligible for Top Campaigns because they lack enough advertising data.
- If frontend dependency installation is blocked by registry/proxy access, typecheck/build validation must be repeated in an approved dependency-cache environment.
- Advertising import remains not pilot-ready while deployed manual import staging QA is blocked.

## Sprint 4.3.2 Advertising Insights Validation Blockers

- The Sprint 4.3/4.3.1 advertising insights code still requires frontend build validation in an environment with approved npm dependency access; this environment cannot restore dependencies because the registry/proxy denies `@tanstack/react-query` and no lockfile is available for `npm ci`.
- `/advertising` browser QA, mobile widths, and dark/light theme verification remain pending until either dependencies are restored for a local browser run or secure staging access is provided outside the report.
- Backend runtime validation is limited to `compileall` here; `pytest` and FastAPI app import require backend dependencies that the Python package proxy currently blocks.
- This is an environment validation blocker, not a new advertising feature blocker: no backend/API enum values, deployment architecture, Meta Ads behavior, or persisted decision-status enums should be changed to work around it.

## Sprint 4.3.3 Frontend Dependency Reproducibility Blocker

- `frontend/package.json` is npm-based, but no authoritative `frontend/package-lock.json` exists yet; this prevents deterministic `npm ci` in CI and local validation environments.
- `npm install --package-lock-only` is blocked here by a registry/proxy `403 Forbidden` response for `@tanstack/react-query`; the lockfile must be generated from an approved npm registry/cache rather than hand-written.
- Until the lockfile exists and dependencies can be restored, frontend typecheck/build and local `/advertising` browser/mobile/theme QA remain environment-blocked.
- CI should treat `frontend/package-lock.json` as the future authoritative lockfile and should fail if it drifts from `frontend/package.json` once it is committed.

## Sprint 4.5 — Advertising reporting readiness limits

- `/advertising` is consolidated as an owner-facing MVP report for manual/CSV-imported ad metrics, campaign insights, manual attribution clarity, and pilot readiness status.
- The readiness block is informational and does not mark the advertising module production-ready.
- Advertising import remains not pilot-ready until deployed staging import QA passes with synthetic data.
- Sprint 4.4 manual attribution remains conditionally approved until PostgreSQL runtime migration QA and browser/mobile attribution QA are completed.
- Meta Ads API OAuth, automatic sync, and automatic attribution remain future work and are not active.

## Sprint 4.5.1 — Staging/runtime QA blocked

- Advertising pilot readiness cannot be claimed because staging frontend/backend URLs, secure test credentials, a controlled QA workspace, safe PostgreSQL test/staging DB access, migration window approval, and rollback/backup confirmation were not available in this environment.
- PostgreSQL runtime validation for `202607010015_manual_ad_attribution.py` remains blocked; do not run the Alembic upgrade/downgrade/upgrade sequence against production.
- Advertising CSV import, `/advertising`, `/leads`, `/orders`, order detail, workspace/cross-workspace, mobile, and theme QA remain blocked until staging/runtime inputs are provided.
- Advertising import remains not pilot-ready, and Sprint 4.4 remains conditionally approved until runtime and browser QA pass with synthetic data.

## Sprint 4.6 — Meta Ads readiness limitation

- Meta Ads API is planned and architecture-ready only; live OAuth, live API calls, token storage implementation, automatic sync jobs, automatic attribution, and Conversions API were not implemented.
- Manual entry and CSV import remain the current MVP advertising data source.
- Future Meta read-only sync must import delivery metrics only; Sellora orders, revenue, and profit remain internal business data unless a separate Conversions API sprint is legally/privacy reviewed.
- Future Meta OAuth must be OWNER-only, workspace-scoped, protected by state/CSRF validation, and store encrypted tokens without returning raw tokens to the frontend.
- Advertising import remains not pilot-ready and Sprint 4.4 remains conditionally approved until the existing runtime/staging blockers are closed.

## Sprint 4.7 — Fake Meta sync simulation limitation

- Meta Ads API is fake-client / simulation-ready / not active.
- The backend fake client, DTOs, mapper, and dry-run service use synthetic data only and do not perform live Meta API calls.
- No live OAuth, real token storage, production sync jobs, database migrations, automatic attribution, click tracking, or Conversions API were added.
- Manual entry and CSV import remain the current MVP advertising data source.
- Advertising import remains not pilot-ready and Sprint 4.4 remains conditionally approved until runtime/staging blockers are closed.

## Sprint 4.8 — Meta sync preview limitation

- Meta Ads API is fake-client + read-only DB comparison + sync preview ready / not active.
- Sync preview is dry-run only and performs no DB writes.
- Exact Meta identity matching remains future work because `external_source` / `external_campaign_id` fields are not persisted yet.
- Manual/CSV data is protected by default; overlap is flagged as `POTENTIAL_CONFLICT`.
- No live OAuth, live API calls, token storage, database migrations, sync-run persistence, production sync jobs, automatic attribution, click tracking, or Conversions API were added.
- Advertising import remains not pilot-ready and Sprint 4.4 remains conditionally approved until runtime/staging blockers are closed.

## Sprint 4.9 — External identity schema limitation

- Meta Ads API is schema design and sync persistence contract ready / not active.
- Exact Meta identity is still not persisted because Sprint 4.9 intentionally adds no database migration.
- Future safe writes require nullable external identity/source fields, manual/CSV backfill, workspace-scoped indexes, sync-run persistence, and PostgreSQL runtime QA.
- Manual/CSV data is protected by default; Meta-owned rows can update only Meta-owned rows with the same external identity.
- No live OAuth, live Meta API calls, token storage, DB writes for Meta sync, production sync jobs, automatic attribution, click tracking, or Conversions API were added.
- Advertising import remains not pilot-ready and Sprint 4.4 remains conditionally approved until runtime/staging blockers are closed.

## Sprint 4.10 — Runtime-gated migration draft limitation

- Meta Ads API is external identity schema draft prepared / runtime-gated / not active.
- The migration draft adds nullable external identity/source fields and non-unique lookup indexes, but PostgreSQL runtime migration QA is still required before full approval.
- No token storage, `meta_ad_connections`, live OAuth/API, production sync jobs, apply-sync, DB writes from Meta sync, automatic attribution, click tracking, or Conversions API were added.
- Source backfill is intentionally not guessed; unknown historical manual/CSV rows can remain null until safely classified.
- Advertising import remains not pilot-ready and Sprint 4.4 remains conditionally approved until runtime/staging blockers are closed.

## Sprint 4.11 — Meta Ads sync preview UX, feature gate, and admin review flow

Sprint 4.11 keeps Meta Ads API inactive and adds only UX, documentation, and regression coverage for a future review flow. The current active advertising source remains manual entry / CSV import, and advertising import is not pilot-ready until staging/runtime QA is completed.

### User-facing status and feature gate

- Frontend feature gate: `metaAdsSyncPreviewEnabled = false` by default.
- Current visible state: `NOT_ACTIVE` / `COMING_SOON` only.
- Meta Ads API is not active yet; there is no live OAuth route, no token input, no live Meta API call, no apply-sync button, and no production sync trigger.
- The disabled CTA says Meta Ads connection will be available in a future stage and cannot start OAuth or sync.

### Future sync preview UX labels

Display labels are frontend-only and must not become persisted backend/API enum values:

| Backend preview value | Ukrainian label | English label |
| --- | --- | --- |
| `WOULD_CREATE` | Буде створено | Will be created |
| `WOULD_UPDATE` | Буде оновлено | Will be updated |
| `WOULD_SKIP` | Без змін | No changes |
| `POTENTIAL_CONFLICT` | Потребує перевірки | Needs review |
| `NEEDS_EXTERNAL_ID_SUPPORT` | Потрібна підтримка Meta ID | Meta ID support needed |
| `INVALID` | Помилка в даних | Data issue |

### Future admin review flow contract

1. OWNER підключає Meta Ads у майбутньому етапі.
2. Sellora завантажує рекламні метрики у preview mode.
3. OWNER бачить, що буде створено, оновлено, пропущено або потребує перевірки.
4. Sellora не перезаписує ручні/CSV дані автоматично.
5. OWNER підтверджує тільки безпечні зміни у майбутньому apply-flow.
6. Sellora записує sync run після майбутнього підтвердженого запуску.

Sprint 4.11 does not implement steps 1, 5, or 6. Apply-sync, sync-run persistence execution, production sync jobs, token storage, and live OAuth remain future work.

### Manual/CSV protection

Sellora не перезаписує ручні або CSV-рекламні дані автоматично. Sellora does not automatically overwrite manual or CSV advertising data. Meta Ads provides spend, impressions, clicks, and messages where available; orders, revenue, and profit remain Sellora-side business data.

### Future UX states

Documented future states are `NOT_ACTIVE`, `COMING_SOON`, `PREVIEW_AVAILABLE`, `NEEDS_REVIEW`, `CONFLICTS_FOUND`, `READY_TO_APPLY`, `CONNECTED`, `SYNCING`, `SYNC_SUCCESS`, `SYNC_FAILED`, `TOKEN_EXPIRED`, `PERMISSION_MISSING`, and `DISCONNECTED`. Sprint 4.11 may only show `NOT_ACTIVE`, `COMING_SOON`, and feature-gated demo preview states; `CONNECTED`, `SYNCING`, and `SYNC_SUCCESS` remain future states and must not imply a live connection.

### Runtime-gated blockers remain

Sprint 4.10 runtime PostgreSQL migration QA remains skipped/pending, so Sprint 4.10 is not fully approved. Sprint 4.4 PostgreSQL runtime migration QA, advertising CSV import staging QA, browser/mobile/theme QA, and workspace/cross-workspace runtime QA remain open blockers.
