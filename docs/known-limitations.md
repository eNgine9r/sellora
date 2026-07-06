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

## Sprint 4.12 — Meta Ads mock OAuth, RBAC contract, and token safety shell

Sprint 4.12 keeps Meta Ads API inactive and adds only a mock OAuth contract, OWNER-only service authorization checks, token redaction utilities, tests, documentation, and regression coverage. The current active advertising source remains manual entry / CSV import, and advertising import is not pilot-ready until staging/runtime QA is completed.

### Mock OAuth scope

- Mock authorization URL: `https://mock.meta.local/oauth/authorize`.
- Mock flow is service-only; no production route is exposed.
- No real Meta OAuth URL, real Meta permissions, live Meta API call, token persistence, database write, production sync job, apply-sync, or `meta_ad_connections` table is added.
- Mock state is generated server-side and includes `workspace_id`, `user_id`, `nonce`, `issued_at`, `expires_at`, and `purpose = meta_ads_mock_oauth`; it includes no token or secret.
- Real OAuth state persistence remains future work and must be workspace-scoped, user-scoped, expiring, and non-secret-bearing.

### OWNER-only RBAC contract

- OWNER may start the mock connect flow, validate the mock callback, and simulate disconnect.
- MANAGER may view status only and may not connect or disconnect.
- ANALYST remains read-only/no-connect and may not connect or disconnect.
- Frontend hiding is not the protection boundary; service-level authorization rejects non-OWNER roles.
- Workspace context must be validated server-side for future live routes.

### Token safety shell

- Token-like values are masked with `mock_token_************abcd` style output or a fully redacted value.
- Secret-like payload fields are redacted before safe reporting.
- Safe diagnostics use a short one-way fingerprint, not a token value.
- Raw token-like values must never be returned to frontend DTOs, stored, logged, included in audit payloads, or included in string/repr output.
- Encryption persistence is not implemented in Sprint 4.12.

### Mock connection DTO contract

Safe mock DTOs may include `status`, `provider`, `workspace_id`, `connection_mode = mock`, `authorization_url`, `state_expires_at`, `connected = false`, `requires_live_setup = true`, `token_stored = false`, `live_api_enabled = false`, `message`, and user-safe `issues`. They must not include raw token fields, real ad account IDs, real business IDs, real Meta user IDs, customer/order data, or secret fields.

### Future audit event contract

Future audit events are `meta_ads_connect_started`, `meta_ads_connect_completed`, `meta_ads_connect_failed`, `meta_ads_disconnected`, `meta_ads_token_refreshed`, and `meta_ads_permission_missing`. Audit records may include workspace/user context and outcome, but must never include raw tokens, client secrets, cookies, customer PII, or customer/order payloads. Sprint 4.12 does not add a new audit table.

### Runtime-gated blockers remain

Sprint 4.10 runtime PostgreSQL migration QA remains pending, so Sprint 4.10 is not fully approved. Sprint 4.4 PostgreSQL runtime/staging/browser QA blockers, advertising CSV import staging QA, browser/mobile/theme QA, and workspace/cross-workspace runtime QA remain open. Meta sync remains not active, and manual/CSV remains the MVP advertising source.

## Sprint 4.13 — Meta Ads mock API boundary, route RBAC, and audit stubs

Sprint 4.13 keeps Meta Ads API inactive while preparing a backend-only, mock API boundary for future OAuth testing. The mock route prefix is `/integrations/meta-ads/mock`; it is disabled by default through `META_ADS_MOCK_OAUTH_API_ENABLED=false` and does not require any secret to remain inactive.

Mock API contract:

- `GET /integrations/meta-ads/mock/status` returns a safe not-active status with `provider=meta_ads`, `connection_mode=mock`, `connected=false`, `token_stored=false`, and `live_api_enabled=false`.
- `POST /integrations/meta-ads/mock/oauth/start` is OWNER-only, works only when the mock API feature gate is enabled, and returns only the obvious mock URL `https://mock.meta.local/oauth/authorize`.
- `POST /integrations/meta-ads/mock/oauth/callback` is OWNER-only, validates signed mock state, rejects invalid/expired/mismatched state, masks and discards synthetic token-like values, and returns only token-safety metadata.
- `POST /integrations/meta-ads/mock/disconnect` is OWNER-only and returns a non-persistent mock disconnect acknowledgement.

Route-level RBAC mirrors the Sprint 4.12 service contract: OWNER may start/callback/disconnect in mock mode when explicitly enabled for tests/dev; MANAGER and ANALYST are denied connect-like actions. Status viewing remains read-only. Frontend hiding is not the only protection.

Audit event stubs are non-persistent DTOs only. They document future events such as `meta_ads_mock_connect_started`, `meta_ads_mock_connect_callback_validated`, `meta_ads_mock_connect_denied`, `meta_ads_mock_disconnected`, and `meta_ads_mock_status_viewed`; no audit table or migration is added. Stub payloads must not include raw tokens, client secrets, cookies, customer/order data, or live account identifiers.

Safety guarantees for this sprint:

- no live Meta OAuth was implemented;
- no facebook.com OAuth redirect or graph.facebook.com API call was added;
- no real Meta OAuth URL, token storage, token input field, `meta_ad_connections` table, database migration, apply-sync, DB write, or production sync job was added;
- manual entry / CSV import remains the active MVP advertising source;
- Meta sync remains not active;
- Sprint 4.12 remains conditionally approved until frontend dependency recovery and browser/mobile QA are completed;
- Sprint 4.10 runtime PostgreSQL migration QA remains pending;
- Sprint 4.4 PostgreSQL runtime/staging/browser QA blockers remain open;
- advertising import is not pilot-ready.

## Sprint 4.14 — Advertising 4.x freeze and Part 5 handoff

Advertising is feature-frozen for now. Advertising is architecture-ready and locally validated, but Advertising is not pilot-ready and Advertising import is not pilot-ready.

Final Advertising 4.x status: **Advertising 4.x — architecture-ready / locally validated / feature-frozen / not pilot-ready**.

Meta Ads status: **Meta Ads API — mock/future-ready / not active**.

Manual/CSV remains the active source. Meta Ads API remains not active. Live OAuth/token storage/apply-sync are future work. Runtime/staging blockers are tracked separately in `docs/advertising-known-blockers.md`.

Part 5 may use Advertising data only as conditional manual/CSV source. Finance 5.x must not depend on live Meta OAuth, token storage, automatic attribution, apply-sync, production sync jobs, or unresolved runtime/staging QA.

Sprint 4.10 runtime PostgreSQL migration QA remains pending. Sprint 4.11 browser/mobile/theme QA remains pending. Sprint 4.12 browser/mobile QA remains pending. Sprint 4.4 PostgreSQL runtime/staging/browser QA blockers remain open.

## Finance 5A known limitations

Finance 5A is not full бухгалтерія and does not include bank statement import, payment gateway reconciliation, tax accounting, or a complete expenses ledger.

Finance uses Advertising data only as conditional manual/CSV source until Advertising runtime/staging blockers are resolved.

Meta Ads API is not active.

Discount fields are not available in the current finance schema, and cancelled/returned/refunded orders are excluded from revenue to avoid double-counting refunds. Shipment costs may be incomplete if shipment data is missing.

## Finance 5B known limitations

Manual finance adjustments improve profit accuracy but are owner-entered and may be incomplete. They are not a full accounting ledger and do not include tax reporting, bank import, payment gateway reconciliation, payroll, invoices, or fiscal receipts.

The `finance_adjustments` migration requires safe PostgreSQL runtime QA before production migration approval.

Advertising data remains a conditional manual/CSV source until runtime/staging blockers are resolved.

Meta Ads API is not active.

## Epic Sprint 5C — Finance stabilization limitations

- Finance adjustments migration has passed static Alembic chain validation, but PostgreSQL runtime migration QA remains pending until tested against a safe staging/test database.
- Browser/mobile QA for `/finance` remains pending when Playwright or staging browser access is unavailable; static regression scripts are not screenshot QA.
- Sellora Finance is operational profit analytics, not full accounting or tax reporting.
- Advertising data remains a conditional manual/CSV source until runtime/staging blockers are resolved.
- Meta Ads API is not active, and Part 6 Meta API work will be handled in separate dedicated sprints.

## Sprint 6A — Meta API readiness limitations

Meta Ads API is not active.

Sprint 6A prepares setup, security, OAuth, token storage, and QA design only. No live OAuth, no token storage, no live API calls, no real Meta app credentials, no real ad account data, no `meta_ad_connections` migration, and no production sync were implemented.

Advertising remains feature-frozen and not pilot-ready. Finance 5.x remains locally validated with runtime migration QA and browser/mobile QA blockers tracked separately.

## Sprint 6A.1 — legal and staging prerequisites limitations

Meta Ads API is not active.

Sprint 6A.1 prepares legal URLs, staging URL inventory, Meta App input pack, OAuth redirect URI planning, and environment variable planning only. No live OAuth, no token storage, no live API calls, no production sync, and no `meta_ad_connections` migration were implemented.

Legal pages are MVP drafts and require legal review before production launch, payment activation, or Meta App Review submission. Staging URL values remain placeholders until real public staging URLs are supplied.

## Sprint 6B — Meta encrypted connection foundation

Sprint 6B adds encrypted token storage infrastructure and connection records behind feature gates.

Meta Ads API is not sync-active.

Live sync, scheduled jobs, apply-sync, and Conversions API are not implemented.

Real OAuth validation requires staging URLs, legal review, Meta App setup, and safe PostgreSQL runtime migration QA.

Advertising remains feature-frozen and not pilot-ready.

## Sprint 6C — Meta read-only discovery and sync-preview foundation

Sprint 6C adds read-only discovery and sync-preview foundations only.

Meta Ads API is not sync-active.

No scheduled sync jobs, no apply-sync, no ad_metrics writes, no customer/order data transfer, and no Conversions API were implemented.

Manual/CSV remains the active Advertising source.

Advertising remains feature-frozen and not pilot-ready.

Runtime/staging validation is still required before any live sync claim.

## Sprint 6D — Live read-only Meta foundation and staging validation gate

Sprint 6D adds live read-only client foundation and staging validation gate only.

Meta Ads API is not sync-active.

No scheduled sync jobs, no apply-sync, no ad_metrics writes, no ad_campaigns writes, no customer/order data transfer, and no Conversions API were implemented.

Manual/CSV remains the active Advertising source.

Advertising remains feature-frozen and not pilot-ready.

Real staging OAuth validation, runtime migration QA, Meta App setup, legal review, and browser/mobile QA are still required before pilot-ready claims.

## Sprint 6E — Runtime/Staging QA gate

Sprint 6E is a QA/risk-closure sprint for the existing Meta Ads foundations.

Result: **BLOCKED** because confirmed safe non-production PostgreSQL runtime migration QA, real Meta OAuth staging validation, Meta Developer App setup, legal review, staging URLs, role-specific test accounts, safe connected workspace validation, and browser/mobile staging smoke QA were unavailable.

Meta Ads API is not production sync-active. Advertising remains feature-frozen and not pilot-ready. No scheduled sync jobs, no apply-sync, no ad_metrics writes, no ad_campaigns writes, no customer/order data transfer, and no Conversions API were implemented.

## Sprint Admin Roles & Users limitations

- Email invitations are not implemented.
- Password reset is not implemented in this sprint.
- Force password change is not implemented.
- User profile editing is not implemented.
- Billing/plans are not implemented.
- Organization-level super admin is not implemented.
- Audit log UI is not implemented.
- Reactivation of inactive workspace user is future work.

## Sprint 7A pending QA

- Staging runtime QA must be completed from an environment that can reach the Vercel and Render staging URLs.
- PostgreSQL runtime migration QA for `202607050019_admin_roles_users` remains pending on a safe non-production database.
- Manual mobile checks at 375px, 390px, 430px, and 768px remain required.

## Sprint 7A.1 staging QA blocker

Manual staging QA for OWNER, MANAGER, ANALYST, workspace switching, team management, mobile More sheet, data isolation, and runtime migration remains blocked in this container because staging URLs return proxy `CONNECT tunnel failed, response 403`.

## Sprint 7F runtime migration blocker

Runtime PostgreSQL migration QA remains blocked in this container by database host resolution failure. No schema mutation was executed; retry from a network that can resolve and reach the safe non-production PostgreSQL host.
