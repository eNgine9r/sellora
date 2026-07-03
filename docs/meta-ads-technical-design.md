# Meta Ads Technical Design — Sprint 4.6 Draft

This is a future implementation contract. It does not add live Meta OAuth, live API calls, token storage logic, sync jobs, or database migrations.

## Proposed backend module boundaries

Future code should keep provider-specific logic isolated under a dedicated integration module, for example:

```text
backend/app/integrations/meta_ads/
  oauth_service.py
  token_service.py
  sync_service.py
  client.py
  schemas.py
  repository.py
```

Responsibilities:

- `client.py`: thin Meta API client wrapper with no business rules; fake client in tests.
- `oauth_service.py`: state generation, callback validation, code exchange orchestration.
- `token_service.py`: token encryption/decryption, refresh scheduling, revoke/disconnect support.
- `sync_service.py`: workspace-scoped campaign and daily metrics sync workflow.
- `repository.py`: database access for Meta connection/account/sync-run records.
- `schemas.py`: request/response contracts that never expose raw tokens.

## Service boundaries

- API routes stay thin and perform auth/RBAC dependency wiring only.
- Services own OAuth validation, workspace checks, sync orchestration, idempotency, and audit events.
- Repositories own database reads/writes and always filter by `workspace_id`.
- Provider clients never know about Sellora RBAC or workspace policies beyond inputs passed by services.

## Future routes

Proposed routes, all workspace-scoped and backend-enforced:

| Route | Method | Role | Purpose |
| --- | --- | --- | --- |
| `/api/v1/integrations/meta/oauth/start` | POST | OWNER | Create state and return official Meta OAuth URL. |
| `/api/v1/integrations/meta/oauth/callback` | GET | server callback | Validate state and exchange token server-side. |
| `/api/v1/integrations/meta/status` | GET | OWNER / allowed read roles | Show masked connection and sync status. |
| `/api/v1/integrations/meta/accounts` | GET | OWNER | List connected ad accounts after OAuth. |
| `/api/v1/integrations/meta/accounts/select` | POST | OWNER | Select workspace ad account. |
| `/api/v1/integrations/meta/sync` | POST | OWNER initially | Trigger read-only sync for a date range. |
| `/api/v1/integrations/meta/disconnect` | POST | OWNER | Revoke/disable connection and audit the event. |

## Future schemas

Response schemas must expose only safe fields:

- connection status;
- provider name;
- masked account/business display name;
- selected account label;
- sync status;
- last successful sync timestamp;
- last safe error category/message.

Response schemas must never expose:

- raw access token;
- refresh token;
- app secret;
- unmasked ad account ID;
- business ID;
- OAuth code;
- workspace ID in user-facing copy.

## Token encryption approach

- Exchange and refresh tokens server-side only.
- Encrypt tokens before persistence using existing secret utilities or an approved KMS/envelope encryption approach.
- Store token expiration and scopes without exposing token values.
- Mask connection/account state in UI.
- Never log token payloads, OAuth callbacks, authorization headers, or raw provider responses.

## Sync job approach

Initial sync should be manual and read-only. Scheduled sync should wait until manual sync is validated in staging.

Required sync behavior:

- sync by selected workspace connection;
- sync by explicit date range;
- paginate through Meta insights safely;
- use backoff for rate limits;
- write sync runs with status: queued/running/succeeded/failed/partial;
- record partial failures per date range where useful;
- retry failed date ranges without duplicating metrics;
- keep manual and CSV import data available if Meta sync fails.

## Idempotency and conflict handling

Future upsert key should consider:

```text
workspace_id + sync_source + external_campaign_id + metric_date
```

Manual/import rows must not be silently overwritten by Meta rows. If a campaign/date has both manual/import and Meta-sourced values, the UI must show source and conflict behavior clearly before any overwrite/merge action.

## Audit logging

Audit events should be created for:

- Meta OAuth start;
- Meta OAuth connected;
- token refresh failed;
- ad account selected;
- manual sync triggered;
- sync succeeded;
- sync failed or partially failed;
- connection disconnected/revoked.

Audit logs must not include raw tokens, raw authorization headers, raw provider payloads, private customer data, or unmasked account identifiers.

## Test plan

Required future tests:

- OAuth state is random, expiring, workspace-scoped, and one-time use.
- Non-OWNER cannot connect/disconnect.
- Workspace A cannot read or sync Workspace B connection.
- Token is encrypted before storage and never appears in response schemas.
- Fake Meta client sync creates/updates campaign and metric rows idempotently.
- Manual/import rows are not silently overwritten by Meta rows.
- Rate-limit and partial failure paths create safe sync statuses.
- Disconnect disables the connection and prevents future sync.

## Staging QA checklist

Before claiming Meta sync readiness in a future sprint:

- Use a controlled staging Meta app and non-production test assets.
- Use secure credentials provided outside the report.
- Do not include real tokens, app secrets, account IDs, business IDs, cookies, workspace IDs, screenshots with secrets, or customer data in QA artifacts.
- Confirm OWNER-only connect/disconnect.
- Confirm token never appears in frontend state, logs, browser console, screenshots, or API responses.
- Confirm workspace isolation with two test workspaces.
- Confirm manual/CSV import fallback still works after connection failure.
- Confirm advertising import remains not pilot-ready unless staging import QA has passed separately.

## Sprint 4.7 implemented fake boundary

Implemented backend skeleton:

```text
backend/app/integrations/meta_ads/
  __init__.py
  schemas.py
  client.py
  fake_client.py
  mapper.py
  sync_service.py
```

Scope:

- `schemas.py` defines typed DTOs and sync candidates for synthetic Meta-like accounts, campaigns, insights rows, issues, and dry-run results.
- `client.py` defines the `MetaAdsClientProtocol` interface: `list_ad_accounts()`, `list_campaigns(account_id)`, and `get_campaign_insights(account_id, date_from, date_to)`.
- `fake_client.py` returns deterministic synthetic accounts, campaigns, zero-denominator rows, and partial/no-data scenarios using fake IDs such as `fake_act_001` and `fake_campaign_001`.
- `mapper.py` maps Meta campaign/insights DTOs into internal sync candidates without writing to the database and without adding orders, revenue, or net profit from Meta.
- `sync_service.py` performs pure dry-run simulation, returns user-safe issues, and never writes to the database.

Still not implemented:

- live OAuth;
- live Meta API calls;
- real token storage;
- production routes;
- scheduled production sync jobs;
- database migrations;
- automatic attribution;
- Conversions API.

Future persistence still requires additive external-source fields and conflict policy before a live sync can write rows. Manual/CSV import remains the active MVP path and must stay available as a fallback.

## Sprint 4.8 implemented sync preview boundary

Implemented read-only preview additions:

```text
backend/app/integrations/meta_ads/repository.py
backend/app/integrations/meta_ads/preview_service.py
backend/tests/test_meta_ads_sync_preview.py
```

`repository.py` defines read-only snapshots and the `AdvertisingSyncReadRepository` protocol. It has only `list_campaign_snapshots(workspace_id)` and `list_metric_snapshots(workspace_id, date_from, date_to)` read methods; no create/update/delete methods, no flush, no commit, and no dependency on a live Meta API.

`preview_service.py` compares fake Meta sync candidates against read-only Sellora snapshots and returns `MetaSyncPreviewResultDTO` with campaign items, metric items, issues, summary counters, `dry_run = true`, and `db_writes = false`.

Campaign comparison policy:

- Future exact identity: `workspace_id + external_source + external_campaign_id` once schema support exists.
- Current Sprint 4.8 fallback: `workspace_id + normalized campaign name + platform`.
- No match becomes `WOULD_CREATE`.
- One safe match becomes `WOULD_SKIP` or `WOULD_UPDATE` depending safe field differences.
- Multiple matches become `POTENTIAL_CONFLICT`.
- Every fallback preview includes `NEEDS_EXTERNAL_ID_SUPPORT` context because Sellora does not yet persist external Meta IDs.

Metric comparison policy:

- Future exact identity: `workspace_id + external_source + external_campaign_id + metric_date`.
- Current fallback: matched campaign + `metric_date`.
- No matching metric becomes `WOULD_CREATE`.
- Existing manual/CSV metric overlap becomes `POTENTIAL_CONFLICT`, not an update.
- Ambiguous campaign matching makes related metrics `POTENTIAL_CONFLICT`.
- Meta delivery/engagement candidates include spend, impressions, clicks, messages, and leads only; orders, revenue, and net profit remain Sellora-side business data.

Conflict copy:

- EN: `This campaign may already exist by name/platform, but Sellora does not yet store Meta external IDs. Review before enabling live sync.`
- UK: `Ця кампанія може вже існувати за назвою/платформою, але Sellora ще не зберігає зовнішні Meta ID. Перевірте перед увімкненням live-синхронізації.`

Still not implemented: live OAuth, live Meta API calls, token storage, database migrations, sync-run persistence, production sync jobs, DB writes from preview, automatic attribution, click ID tracking, and Conversions API.

## Sprint 4.9 — External identity schema, migration plan, and persistence contract

Sprint 4.9 is a design/contract sprint only. Meta Ads API status is **schema design and sync persistence contract ready / not active**. Manual entry and CSV import remain the active MVP source. No live Meta OAuth, no live Meta API calls, no token storage, no database migration, no sync-run persistence implementation, no production sync job, and no DB writes are added for Meta sync.

### Current limitation audit

Current Sprint 4.8 preview can compare by existing fields only: workspace, normalized campaign name/platform, matched campaign, and metric date. Exact Meta identity is missing because campaigns and metrics do not persist `external_source`, `external_account_id`, or `external_campaign_id`. Name/platform matching is useful for dry-run review, but it is not safe for automatic writes because it can be ambiguous and can overlap with owner-maintained manual/CSV data.

Manual/CSV rows must not be overwritten because they may include owner-entered corrections, imported historical spreadsheet rows, manually attributed orders, revenue, and net profit. Future exact idempotency requires `workspace_id` plus external source/account/campaign identifiers and, for metrics, `metric_date`. Future sync-run records are required to audit who triggered a run, which date range/account was used, what changed, what conflicted, and whether the run was dry-run or apply-run. Every future schema change requires PostgreSQL runtime QA before staging or production approval.

### Future `ad_campaigns` external identity fields

Proposed additive campaign fields, nullable first:

| Field | Design value / purpose |
| --- | --- |
| `external_source` | Provider value such as `meta_ads`. |
| `external_account_id` | Provider account identifier; never used without `workspace_id`. |
| `external_campaign_id` | Provider campaign identifier; never used without `workspace_id`. |
| `external_status` | Provider status for diagnostics and reporting. |
| `external_objective` | Provider objective for diagnostics and reporting. |
| `last_synced_at` | Timestamp of last successful provider sync for the campaign. |
| `sync_source` | Source/owner marker: `manual`, `csv_import`, or `meta_sync`. |

Future campaign uniqueness concept:

```text
workspace_id + external_source + external_account_id + external_campaign_id
```

Rules: these are future design values only unless a migration is explicitly approved; backend values remain English; external IDs are always workspace-scoped; external IDs must never be trusted without `workspace_id`; do not add persisted `GOOD`, `WATCH`, `PROBLEM`, or `NO_DATA` enums.

### Future `ad_metrics` source separation fields

Proposed additive metric fields, nullable first:

| Field | Design value / purpose |
| --- | --- |
| `source_type` | Row source: `manual`, `csv_import`, or `meta_sync`. |
| `external_source` | Provider value such as `meta_ads` for synced rows. |
| `external_account_id` | Provider account identifier for synced rows. |
| `external_campaign_id` | Provider campaign identifier for synced rows. |
| `last_synced_at` | Timestamp of last successful provider sync for the metric row. |
| `sync_run_id` | Optional link to the future `meta_sync_runs` audit/debug row. |

Future Meta metric idempotency concept:

```text
workspace_id + external_source + external_account_id + external_campaign_id + metric_date
```

Meta-synced rows must not silently overwrite manual/CSV rows. Meta provides spend, impressions, clicks, and messages/leads where available. Orders, revenue, and net profit remain Sellora-side business metrics and must not be imported from Meta Ads Insights unless a separate Conversions API sprint is legally/privacy reviewed and explicitly approved.

### Future `meta_sync_runs` persistence contract

Future table: `meta_sync_runs`.

Suggested fields:

```text
id
workspace_id
connection_id
external_account_id
sync_type
status
date_from
date_to
started_at
finished_at
triggered_by_user_id
campaigns_seen
metrics_seen
campaigns_created
campaigns_updated
metrics_created
metrics_updated
skipped
conflicts
errors_count
error_summary
dry_run
created_at
updated_at
```

Suggested status values: `pending`, `running`, `success`, `partial_failed`, `failed`, and `cancelled`.

Contract rules:

- no secrets in sync runs;
- no raw tokens, authorization headers, OAuth codes, or provider payload dumps in errors;
- no customer PII or private order details;
- every sync run is scoped by `workspace_id`;
- sync runs are audit/debug objects, not business metric sources by themselves;
- dry-run and apply-run must be distinguishable with `dry_run` and safe counters.

Optional future table: `meta_sync_run_items`, used only if item-level create/update/skip/conflict details are needed for debugging and audit.

### Future `meta_ad_connections` schema contract

Future table: `meta_ad_connections`.

Suggested fields:

```text
id
workspace_id
provider
status
connected_by_user_id
scopes
token_encrypted_ref
token_expires_at
last_successful_sync_at
last_failed_sync_at
disconnected_at
created_at
updated_at
deleted_at
```

Do not implement token storage in Sprint 4.9. This schema is a future contract only. Future token storage must encrypt the token before persistence, never return raw tokens to frontend responses, never write tokens to logs, and allow only OWNER to connect/disconnect. Disconnect should revoke the provider token if supported by the live implementation.

### Staged migration plan — design only

| Phase | Plan |
| --- | --- |
| Phase A | Design only: document external identity, source separation, sync-run persistence, connection storage, and conflict rules. |
| Phase B | Add nullable external identity fields on `ad_campaigns` and `ad_metrics`. |
| Phase C | Backfill existing campaigns/metrics as `manual` or `csv_import` while preserving all existing values. |
| Phase D | Add workspace-scoped indexes and uniqueness protections for exact Meta identity. |
| Phase E | Add `meta_sync_runs` and optional `meta_sync_run_items` after preview/apply requirements are validated. |
| Phase F | Validate Alembic upgrade/downgrade/upgrade on a safe PostgreSQL database. |
| Phase G | Run staging QA with synthetic data, manual/CSV fallback checks, workspace isolation, and rollback confirmation. |

Migration rules: all new fields are nullable first; existing data remains valid; manual/CSV rows are protected; downgrade path is documented before merge; PostgreSQL runtime QA is required before approval; no production migration runs without backup and rollback windows. Sprint 4.9 does not create or apply an Alembic migration.

### Conflict resolution contract

Manual/CSV data is protected by default. Meta-synced rows can update only Meta-owned rows with the same external identity. If a Meta row overlaps with manual or CSV data, flag a conflict. If campaign matching is ambiguous by name/platform, flag a conflict. Do not import orders, revenue, or net profit from Meta Ads Insights. Do not auto-link Meta data to Sellora orders unless a separate attribution sprint is approved.

User-safe conflict copy:

- EN: `This row overlaps with existing manual or CSV advertising data. Sellora will not overwrite it automatically.`
- UK: `Цей рядок перетинається з існуючими ручними або CSV-рекламними даними. Sellora не перезапише його автоматично.`

### Preview-to-apply-sync contract

Future apply-sync should follow this sequence:

1. Fetch Meta data through the client.
2. Map to sync candidates.
3. Compare through the read-only repository.
4. Produce preview.
5. User/admin reviews conflicts.
6. Apply only safe Meta-owned create/update operations.
7. Record `meta_sync_run`.
8. Record item-level conflicts if enabled.
9. Keep manual/CSV rows untouched.

Sprint 4.9 does not implement step 6. No DB writes are added for Meta sync, and preview remains the safe boundary until external identity schema support is implemented and validated.

## Sprint 4.10 — Runtime-gated external identity schema draft

Sprint 4.10 implements the first safe schema preparation step for future Meta sync while keeping Meta Ads API **external identity schema draft prepared / runtime-gated / not active**. It adds only nullable external identity/source-separation fields and read-only preview compatibility. It does not implement live Meta OAuth, live Meta API calls, token storage, `meta_ad_connections`, production sync jobs, apply-sync, Conversions API, or DB writes from Meta sync.

### Audit result before coding

- `ad_campaigns` exists and currently stores workspace-scoped campaign metadata: `name`, `platform`, `status`, `objective`, `budget_type`, budgets, date range, notes, soft delete, timestamps, metrics, leads, and orders.
- `ad_metrics` exists and currently stores workspace-scoped daily campaign metrics: `campaign_id`, `metric_date`, spend, impressions, reach, clicks, messages, leads, orders, revenue, net profit, soft delete, timestamps, and campaign relationship.
- No source/import/external identity fields existed on these models before the Sprint 4.10 draft.
- Existing Alembic revisions use timestamp IDs and explicit upgrade/downgrade functions; the new draft follows that style with revision `202607010016` after `202607010015`.
- Manual/CSV import continues to use existing advertising services and must not change in this sprint.

### Migration draft result

Draft migration: `backend/alembic/versions/202607010016_meta_ads_external_identity_fields.py`.

The migration is additive, nullable-first, downgrade-safe, existing-data-safe, PostgreSQL-compatible, and independent of live Meta API/token storage. It does not create token storage, OAuth tables, `meta_ad_connections`, production sync jobs, apply-sync persistence, or persisted decision enums.

### Fields added to `ad_campaigns`

| Field | Type | Nullable | Purpose |
| --- | --- | --- | --- |
| `external_source` | `String(50)` | yes | Future provider such as `meta_ads`. |
| `external_account_id` | `String(128)` | yes | Future provider account identity, always workspace-scoped. |
| `external_campaign_id` | `String(128)` | yes | Future provider campaign identity, always workspace-scoped. |
| `external_status` | `String(64)` | yes | Provider status snapshot for diagnostics. |
| `external_objective` | `String(128)` | yes | Provider objective snapshot for diagnostics. |
| `last_synced_at` | `DateTime(timezone=True)` | yes | Future sync timestamp. |
| `sync_source` | `String(32)` | yes | Future source marker: `manual`, `csv_import`, or `meta_sync`. |

Index draft: `ix_ad_campaigns_workspace_external_identity` on `workspace_id + external_source + external_account_id + external_campaign_id`, non-unique until safe backfill and runtime QA allow a future uniqueness decision.

### Fields added to `ad_metrics`

| Field | Type | Nullable | Purpose |
| --- | --- | --- | --- |
| `source_type` | `String(32)` | yes | Future source marker: `manual`, `csv_import`, or `meta_sync`. |
| `external_source` | `String(50)` | yes | Future provider such as `meta_ads`. |
| `external_account_id` | `String(128)` | yes | Future provider account identity. |
| `external_campaign_id` | `String(128)` | yes | Future provider campaign identity. |
| `last_synced_at` | `DateTime(timezone=True)` | yes | Future sync timestamp. |
| `sync_run_id` | `UUID` | yes | Nullable, non-FK until `meta_sync_runs` exists. |

Index draft: `ix_ad_metrics_workspace_external_identity_date` on `workspace_id + external_source + external_account_id + external_campaign_id + metric_date`, non-unique until backfill and runtime QA are complete.

### Downgrade strategy

Downgrade drops `ix_ad_metrics_workspace_external_identity_date`, removes the six `ad_metrics` fields, drops `ix_ad_campaigns_workspace_external_identity`, and removes the seven `ad_campaigns` fields. No destructive data rewrite or backfill is part of the migration draft.

### Backfill plan

Sprint 4.10 does not guess historical ownership and does not mass-update existing rows. New fields remain nullable.

Future backfill plan:

- manually created campaigns/metrics: `sync_source` / `source_type = manual` only when safely identifiable;
- CSV-imported metrics: `source_type = csv_import` only when source can be safely determined;
- unknown historical rows: source fields remain `null` until reviewed or classified by a safe rule.

No financial formula, attribution calculation, import behavior, or lead/order campaign attribution behavior changes in Sprint 4.10.

### SQLAlchemy model and preview compatibility

`AdCampaign` and `AdMetric` models expose the new nullable columns with matching names and no required defaults. The read-only snapshot repository exposes optional external identity/source fields. The sync preview matching priority is now:

1. exact external identity when `external_source + external_account_id + external_campaign_id` is present;
2. safe normalized name/platform fallback;
3. conflict if fallback matching is ambiguous;
4. `NEEDS_EXTERNAL_ID_SUPPORT` context when exact identity is unavailable.

Preview remains no-write: no `commit`, no `flush`, no apply-sync, no production route, no token usage, and no live Meta API call.

### Runtime-gated policy

Static Alembic validation may run locally with `alembic heads` and `alembic history --verbose`. PostgreSQL runtime migration QA (`alembic upgrade head`, `alembic downgrade -1`, `alembic upgrade head`) must run only on a safe non-production database. If a safe PostgreSQL database is unavailable, runtime QA remains blocked and Sprint 4.10 can only be conditionally approved after static/build/test checks pass.

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

## Sprint 6A — secure live-readiness design boundary

Meta Ads API is not active.

Sprint 6A is documentation and guardrail work only. It prepares setup, security, OAuth, token storage, and QA design; it does not add live OAuth routes, real Meta redirects, token persistence, a `meta_ad_connections` migration, live API calls, apply-sync, production sync jobs, or Conversions API.

Future implementation must keep provider logic isolated, tokens encrypted and never returned to the frontend, connection records workspace-scoped, OWNER connect/disconnect enforced on the backend, and audit payloads free of raw tokens, authorization codes, customer PII, order payloads, cookies, and database URLs.
