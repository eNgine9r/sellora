# Meta Ads Integration Plan — Sprint 4.6 Readiness Contract

Sprint 4.6 prepares Sellora for a future Meta Ads API integration. It does **not** implement live Meta OAuth, token storage, ad account connection, automatic sync jobs, automatic attribution, Conversions API, or any live Meta API calls.

Current MVP source remains **manual entry / CSV import**. Meta Ads API status after Sprint 4.6 is **planned / architecture-ready / not active**.

## Current advertising architecture audit

### What exists today

- `AdCampaign` is workspace-scoped, soft-deletable, and stores `name`, `platform`, `status`, `objective`, `budget_type`, optional budgets, date range, and notes.
- `AdMetric` is workspace-scoped, soft-deletable, and stores one daily row per `campaign_id + metric_date` with spend, impressions, reach, clicks, messages, leads, orders, revenue, and net profit.
- Lead/order manual attribution stores nullable `campaign_id` on leads and orders and exposes friendly `campaign_name` in responses/UI.
- `/advertising` reports manual/CSV-imported metrics, campaign insights, manual attribution guidance, and pilot readiness warnings.
- Import Center can map advertising rows into campaigns and daily ad metrics from synthetic/manual CSV data.

### Ready for future Meta sync

- Workspace-scoped campaign and metric entities already match the core Meta daily-insights shape.
- Existing formulas safely handle zero denominators and unavailable values.
- Existing integration connection and credential concepts show the intended workspace-scoped encrypted-secret pattern.
- Manual/CSV import fallback is already documented and must remain available even after future Meta sync exists.

### Missing before live Meta sync

- No Meta provider enum, OAuth route, callback route, token exchange service, or Meta client exists yet.
- No external Meta IDs are stored on campaigns/metrics yet.
- No sync run table, sync job, retry queue, rate-limit handling, or account selection UI exists yet.
- No legal/privacy-reviewed Conversions API flow exists.

### Must not change before staging QA

- Do not mark advertising import pilot-ready until staging CSV import QA passes with synthetic data.
- Do not mark Sprint 4.4 attribution fully approved until PostgreSQL runtime migration QA and browser/mobile attribution QA pass.
- Do not replace manual/import metrics with fake Meta API data.

## Integration phases

| Phase | Scope | Required Meta permissions | Data pulled from Meta | Data stored in Sellora | Workspace rules | Privacy risks | Rollback plan | Explicitly not included |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Phase 0 — Manual / CSV import MVP | Current MVP source remains manual daily metrics and CSV import. | None. | None. | Existing campaigns and ad metrics from manual/import sources. | All rows remain scoped by `workspace_id`. | Risk is user-uploaded spreadsheet content; keep synthetic QA and privacy warnings. | Continue manual entry/import; delete bad imported rows through existing flows. | OAuth, live sync, tokens, automatic attribution. |
| Phase 1 — Meta OAuth preparation | Add OWNER-only connection UI, OAuth state generation, callback contract, and encrypted credential storage with fake-client tests. | Future implementation must validate current Meta least-privilege permissions during that sprint. | OAuth account metadata only after user consent. | Workspace-scoped connection, encrypted credential, selected account metadata. | OAuth state resolves workspace server-side; one workspace cannot see another workspace connection. | Token leakage, CSRF, wrong workspace binding. | Disconnect/revoke token if possible, soft-delete connection, clear selected account. | Campaign sync, scheduled jobs, Conversions API. |
| Phase 2 — Read-only campaign and daily metrics sync | Fetch campaigns and daily delivery metrics from selected ad account. | Read-only ads/insights permissions approved by Meta app review. | Campaign metadata, spend, impressions, reach, clicks, and available message/lead delivery metrics. | Future external IDs on campaigns/metrics and daily metric rows marked as Meta-sourced. | Every sync query/write filters by `workspace_id` and selected connection. | Users may assume Meta knows Sellora revenue/profit; UI must explain it does not. | Disable sync, keep manual/import rows, remove or reclassify failed Meta-sourced rows if needed. | Sending customer/order data to Meta, automatic attribution, profit sync from Meta. |
| Phase 3 — Scheduled sync jobs | Add scheduled/background sync with status and retry strategy. | Same as Phase 2. | Incremental daily insights by date range. | Sync runs, last successful sync timestamp, partial failure records. | Scheduler executes per workspace connection only. | Rate limits, stale tokens, partial failures. | Stop schedule, retry failed ranges, keep manual fallback. | Conversions API, optimization writes. |
| Phase 4 — Conversion feedback / Conversions API | Separate legal/privacy-reviewed sprint to send approved conversion events. | Conversions API permissions and explicit legal/privacy approval. | Not a read-only pull; sends approved conversion events. | Consent/audit records and conversion send logs if implemented. | Per-workspace consent and settings. | Customer PII transfer and consent/legal risk. | Disable event sending, revoke token/scope, audit rollback steps. | Any implementation in Sprint 4.6. |
| Phase 5 — Advanced attribution and optimization | Future multi-touch attribution, optimization recommendations, and automated insights. | To be evaluated later. | May combine Meta, Sellora orders, and approved attribution events. | Future additive analytics entities only after design review. | Strict workspace and RBAC boundaries. | Misleading recommendations, privacy risk, over-automation. | Feature flags/off switch, keep manual fallback. | Current MVP or Sprint 4.6 scope. |

## OAuth architecture contract

1. OWNER starts connection from `/settings/integrations` for the current workspace.
2. Backend creates an OAuth state record that binds a random nonce to the workspace and initiating user; the raw workspace ID is not trusted from the callback query alone.
3. Sellora redirects the OWNER to the official Meta OAuth consent screen.
4. Callback validates the state nonce, expiration, actor role, and workspace membership server-side.
5. Backend exchanges the short-lived code/token for a long-lived token server-side.
6. Token is encrypted before storage in a workspace-scoped credential record.
7. Raw token is never returned to frontend, logs, docs, screenshots, or tests.
8. UI shows connection status, connected business/ad account names, masked metadata, and last sync status — never raw tokens.
9. OWNER can disconnect; backend revokes token if supported, soft-deletes or disables the connection, and records an audit event.
10. Connect, disconnect, token refresh failure, account selection, manual sync trigger, and sync failure create audit log entries.

Security requirements:

- CSRF/state protection is mandatory.
- OAuth state must be workspace-scoped and server-validated.
- Tokens must be encrypted at rest.
- Tokens must never be placed in frontend state, browser storage, logs, screenshots, docs, or PR text.
- Only OWNER can connect/disconnect Meta accounts.
- MANAGER may view sync status only if product policy allows.
- ANALYST remains read-only and only sees advertising metrics allowed by existing financial visibility rules.

## Meta data mapping contract

| Meta object | Sellora target | Notes |
| --- | --- | --- |
| Meta Ad Account | Workspace-level integration connection plus future ad account metadata table | Connection belongs to exactly one workspace. |
| Meta Campaign | Existing `AdCampaign` plus future external mapping fields | Campaign remains workspace-scoped and soft-deletable. |
| Meta Ad Set | Future optional dimension | Do not add until reporting needs are validated. |
| Meta Ad | Future optional dimension | Do not add until ad-level reporting is needed. |
| Meta Insights daily row | Existing `AdMetric` plus source/external IDs | Daily sync must be idempotent by workspace/source/campaign/date. |

Future fields to consider, all additive and workspace-scoped where stored:

- `external_source` / `sync_source`;
- `external_account_id` / synthetic-safe account reference;
- `external_campaign_id`;
- optional future `external_adset_id` and `external_ad_id`;
- `last_synced_at`;
- `sync_status`.

Important data rule: **Meta spend, impressions, reach, and clicks come from Meta; orders, revenue, and net profit are Sellora-side business metrics unless a separate future conversion integration is explicitly implemented and legally reviewed.**

## Data ownership and privacy rules

- Sellora owns internal customer, order, shipment, inventory, finance, and profit data.
- Meta Ads API provides ad delivery and spend metrics for an authorized ad account.
- Meta tokens are sensitive secrets and must be encrypted before storage.
- Customer/order data must not be sent to Meta during read-only sync.
- No customer PII may be sent to Meta unless a separate Conversions API sprint includes legal/privacy review, consent design, and explicit product approval.
- Docs, tests, screenshots, fixtures, and PR text must never include real Meta tokens, app secrets, business IDs, ad account IDs, campaign IDs, customer data, workspace IDs, cookies, or private logs.

## Workspace and RBAC contract

- A Meta connection belongs to exactly one workspace.
- Workspace A cannot see, select, sync, or disconnect Workspace B Meta connection or ad account.
- Backend must validate `workspace_id` on every integration request; frontend hiding is not sufficient.
- OAuth state must bind the initiating user and workspace server-side.
- OWNER can connect/disconnect Meta accounts and manage sync settings.
- MANAGER can view advertising metrics and may trigger manual sync only if a future product decision explicitly allows it.
- ANALYST can view advertising metrics only according to existing financial visibility rules and cannot manage credentials.

## Sync design contract

Future read-only sync should support:

- OWNER manual sync trigger;
- scheduled sync jobs after manual sync is proven safe;
- date range sync and incremental sync;
- idempotent upsert behavior;
- duplicate prevention;
- rate-limit backoff;
- partial failure recording;
- retry strategy per workspace/date range;
- sync status and last successful sync timestamp;
- audit logging for trigger, success, failure, and disconnect.

Idempotency requirements:

- The same Meta campaign/date row updates the existing Meta-sourced metric row, not a duplicate.
- Future uniqueness should consider `workspace_id + source + external_campaign_id + metric_date`.
- Manual/import rows and Meta-sourced rows must not silently overwrite each other.
- If manual and Meta rows conflict for the same campaign/date, UI/API must explain source and conflict behavior before overwriting.

## Future UI states and copy

Future UI entry points:

- `/settings/integrations` for connection and account status;
- `/advertising` for source badges, sync status, and manual fallback;
- a future import/sync view only after product approval.

Future UI states:

- Not connected;
- Connecting;
- Connected;
- Syncing;
- Sync successful;
- Sync failed;
- Token expired;
- Permission missing;
- Disconnected.

Required user-facing copy:

- UK: `Meta Ads API ще не активний. Ручне внесення та CSV-імпорт залишаються доступними. Майбутня Meta sync імпортуватиме лише delivery metrics кампаній. Замовлення й прибуток залишаються даними Sellora.`
- EN: `Meta Ads API is not active yet. Manual entry and CSV import remain available. Future Meta sync will import campaign delivery metrics only. Orders and profit still come from Sellora data.`

## Future database proposal — no migration in Sprint 4.6

Possible future tables:

- `meta_ad_connections` for workspace/account connection metadata;
- `meta_ad_accounts` for selected ad account metadata;
- `meta_sync_runs` for sync status, ranges, failures, and retry metadata.

Possible future additive fields:

- on campaigns/metrics: `external_source`, `external_campaign_id`, `external_account_id`, `last_synced_at`, `sync_status`;
- token fields only in credential tables and always encrypted;
- API responses must expose masked status only, never raw tokens.

Sprint 4.6 intentionally adds no Meta database migration.

## Manual attribution compatibility

Campaign selection must remain optional. Future Meta Ads sync may map external campaign identifiers to Sellora campaigns, but it must not require every lead or order to have `campaign_id`, and it must not treat unattributed orders as errors.

Sprint 4.6 readiness docs do not activate OAuth, token exchange, ad account selection, campaign sync, or insights sync.

## Sprint 4.7 — Fake-client sync simulation boundary

Sprint 4.7 adds a backend-only fake-client boundary under `backend/app/integrations/meta_ads/` for safe simulation. Meta Ads API status is now **fake-client / simulation-ready / not active**. Manual entry and CSV import remain the active MVP advertising source.

The fake boundary includes typed DTO contracts, a client protocol, deterministic synthetic fake client, mapping layer, and dry-run sync service. It does not add live OAuth, live Meta API calls, token storage, production routes, scheduled jobs, database migrations, automatic attribution, click tracking, or Conversions API.

Current reusable models remain `AdCampaign` and `AdMetric`. Future live sync still needs additive external source/account/campaign identifiers and sync-run persistence before any database write can happen. Those fields are not persisted in Sprint 4.7.

Dry-run idempotency contract: the future write path should treat `workspace_id + external_source + external_campaign_id + metric_date` as the Meta-sourced daily metric identity. Manual/import rows and Meta-sourced rows must not silently overwrite each other. Orders, revenue, and net profit remain Sellora-side business metrics unless a separate Conversions API sprint is legally/privacy reviewed and explicitly approved.

## Sprint 4.8 — Read-only DB comparison and sync preview

Sprint 4.8 extends the fake-client boundary with read-only DB comparison and structured sync preview. Meta Ads API status is now **fake-client + read-only DB comparison + sync preview ready / not active**. Manual entry and CSV import remain the current MVP advertising data source.

Current comparison can safely use existing fields only: `workspace_id + normalized campaign name + platform` for campaign fallback matching and matched campaign + `metric_date` for metric fallback matching. Exact future behavior still requires `workspace_id + external_source + external_campaign_id`; because Sprint 4.8 adds no database migration, exact external Meta identity persistence is still future work.

Manual/CSV data is protected by default. If a fake Meta metric appears to overlap with an existing manual/CSV row, the preview flags it as `POTENTIAL_CONFLICT` instead of updating it. Ambiguous campaign matching also becomes `POTENTIAL_CONFLICT`, not an automatic update. Preview classifications are internal backend DTO values only: `WOULD_CREATE`, `WOULD_UPDATE`, `WOULD_SKIP`, `POTENTIAL_CONFLICT`, `NEEDS_EXTERNAL_ID_SUPPORT`, and `INVALID`.

Preview results are always dry-run: `dry_run = true`, `db_writes = false`. No live OAuth, live Meta API calls, token storage, production sync jobs, sync-run persistence, database migrations, automatic attribution, click tracking, or Conversions API are active. Orders, revenue, and net profit remain Sellora-side business metrics.

Sprint 4.8 external ID limitation shorthand: future exact sync still needs additive `external_source/external_id` support before live writes are safe; external Meta identity persistence is still future work.

## Sprint 4.9 — External identity schema and sync persistence contract

Sprint 4.9 keeps Meta Ads API **schema design and sync persistence contract ready / not active**. Manual entry and CSV import remain the current MVP advertising data source. This sprint does **not** apply a migration, implement live Meta OAuth, call the live Meta API, store tokens, add DB writes for Meta sync, or make advertising import pilot-ready.

### Current limitation audit

- Exact Meta identity is currently missing because `ad_campaigns` and `ad_metrics` do not persist `external_source`, `external_account_id`, or `external_campaign_id`.
- Sprint 4.8 name/platform matching is only a temporary fallback; two campaigns can share similar names or platform values, so fallback matches must stay preview-only.
- Manual/CSV rows are protected by default because owners may have corrected business metrics, imported spreadsheet data, or manually attributed orders that Meta Ads Insights does not own.
- Exact idempotency requires workspace-scoped external identity fields, not just display names.
- Sync-run records are needed for audit/debugging: who triggered sync, which account/date range was used, what was created/updated/skipped/conflicted, and whether the run was dry-run or apply-run.
- Future schema changes require PostgreSQL runtime QA with Alembic upgrade/downgrade/upgrade before any staging or production approval.

### Future campaign external identity design

Future additive `ad_campaigns` fields, all nullable at first and workspace-scoped when queried:

| Field | Purpose |
| --- | --- |
| `external_source` | Provider identifier such as `meta_ads`. |
| `external_account_id` | Provider account identifier, always used with `workspace_id`. |
| `external_campaign_id` | Provider campaign identifier, always used with `workspace_id` and account/source. |
| `external_status` | Provider campaign status copied for diagnostics/reporting. |
| `external_objective` | Provider objective copied for diagnostics/reporting. |
| `last_synced_at` | Last successful provider sync timestamp for this campaign. |
| `sync_source` | Ownership/source marker: `manual`, `csv_import`, or `meta_sync`. |

Future exact campaign uniqueness concept:

```text
workspace_id + external_source + external_account_id + external_campaign_id
```

These are design values only until a migration is explicitly approved. Backend values stay English, and Sellora must not add persisted `GOOD` / `WATCH` / `PROBLEM` / `NO_DATA` decision enums for this contract.

### Future ad metric source separation

Future additive `ad_metrics` fields, all nullable at first:

| Field | Purpose |
| --- | --- |
| `source_type` | Row owner/source: `manual`, `csv_import`, or `meta_sync`. |
| `external_source` | Provider identifier such as `meta_ads` for synced rows. |
| `external_account_id` | Provider account identifier for synced rows. |
| `external_campaign_id` | Provider campaign identifier for synced rows. |
| `last_synced_at` | Last provider sync timestamp for this metric row. |
| `sync_run_id` | Link to the future sync-run audit/debug record. |

Future exact Meta metric idempotency concept:

```text
workspace_id + external_source + external_account_id + external_campaign_id + metric_date
```

Meta provides spend, impressions, clicks, and messages/leads where available. Orders, revenue, and net profit remain Sellora-side business metrics and must not be imported from Meta Ads Insights unless a separate Conversions API sprint is legally/privacy reviewed and explicitly approved.

### Future sync persistence contract

Future table: `meta_sync_runs`.

Suggested fields: `id`, `workspace_id`, `connection_id`, `external_account_id`, `sync_type`, `status`, `date_from`, `date_to`, `started_at`, `finished_at`, `triggered_by_user_id`, `campaigns_seen`, `metrics_seen`, `campaigns_created`, `campaigns_updated`, `metrics_created`, `metrics_updated`, `skipped`, `conflicts`, `errors_count`, `error_summary`, `dry_run`, `created_at`, and `updated_at`.

Suggested status values: `pending`, `running`, `success`, `partial_failed`, `failed`, and `cancelled`.

Sync runs are workspace-scoped audit/debug objects. They must not contain secrets, raw tokens, raw provider authorization headers, customer PII, or private order data. Dry-run and apply-run must be distinguishable by `dry_run` and by safe summary counters.

Optional future table: `meta_sync_run_items` for item-level create/update/skip/conflict details when debugging or audit requirements justify the additional storage.

### Future Meta connection schema contract

Future table: `meta_ad_connections`.

Suggested fields: `id`, `workspace_id`, `provider`, `status`, `connected_by_user_id`, `scopes`, `token_encrypted_ref`, `token_expires_at`, `last_successful_sync_at`, `last_failed_sync_at`, `disconnected_at`, `created_at`, `updated_at`, and `deleted_at`.

Do not implement token storage in Sprint 4.9. This is schema design only. In a future sprint, tokens must be encrypted before storage, never returned to the frontend, never logged, and managed only through OWNER-only connect/disconnect flows. Disconnect should revoke the provider token if the live implementation supports revocation.

### Staged migration plan — not applied in Sprint 4.9

1. Phase A — design only: document external identity, source separation, sync runs, and connection contracts.
2. Phase B — add nullable external identity fields on `ad_campaigns` and `ad_metrics`.
3. Phase C — backfill existing `ad_campaigns` and `ad_metrics` as `manual` or `csv_import` without changing business values.
4. Phase D — add indexes and uniqueness protections for workspace-scoped external identity.
5. Phase E — add `meta_sync_runs` and optional `meta_sync_run_items` only after preview/apply needs are confirmed.
6. Phase F — validate Alembic upgrade/downgrade/upgrade on a safe PostgreSQL database.
7. Phase G — run staging QA with synthetic Meta-like data and manual/CSV fallback checks.

All new fields should be nullable at first, existing data must remain valid, manual/CSV rows must be protected, downgrade behavior must be documented, PostgreSQL runtime QA is required before approval, and no production migration should run without backup and rollback windows.

### Conflict resolution and preview-to-apply contract

Manual/CSV data is protected by default. Meta-synced rows can update only Meta-owned rows with the same external identity. If a Meta row overlaps with manual/CSV data, Sellora must flag a conflict. If campaign matching is ambiguous by name/platform, Sellora must flag a conflict. Do not import orders, revenue, or net profit from Meta Ads Insights. Do not auto-link Meta data to Sellora orders unless a separate attribution sprint is approved.

User-safe conflict copy:

- EN: `This row overlaps with existing manual or CSV advertising data. Sellora will not overwrite it automatically.`
- UK: `Цей рядок перетинається з існуючими ручними або CSV-рекламними даними. Sellora не перезапише його автоматично.`

Future preview-to-apply flow:

1. Fetch Meta data through the provider client.
2. Map Meta data to sync candidates.
3. Compare candidates through the read-only repository.
4. Produce a preview.
5. User/admin reviews conflicts.
6. Apply only safe Meta-owned create/update operations.
7. Record `meta_sync_run`.
8. Record item-level conflicts if enabled.
9. Keep manual/CSV rows untouched.

Sprint 4.9 must not implement step 6. No DB writes are added for Meta sync.

## Sprint 4.10 — External identity migration draft and runtime gate

Sprint 4.10 prepares an additive, nullable-first schema draft for future Meta-owned campaign/metric separation. Meta Ads API status is **external identity schema draft prepared / runtime-gated / not active**. Manual entry and CSV import remain the current MVP advertising data source. No live Meta OAuth, live Meta API call, token storage, `meta_ad_connections` implementation, production sync job, apply-sync, or Meta sync DB write is added.

### Current schema/model audit result

- Current `ad_campaigns` model fields include workspace/soft-delete/timestamps plus `name`, `platform`, `status`, `objective`, `budget_type`, optional budgets, date range, notes, metrics, leads, and orders.
- Current `ad_metrics` model fields include workspace/soft-delete/timestamps plus `campaign_id`, `metric_date`, spend, impressions, reach, clicks, messages, leads, orders, revenue, net profit, and the campaign relationship.
- Existing models did not have source/import/external identity fields before Sprint 4.10.
- Current Alembic files use timestamp-style revisions such as `202607010015_manual_ad_attribution.py`; Sprint 4.10 follows that style with `202607010016_meta_ads_external_identity_fields.py`.
- Manual/CSV import currently creates normal campaigns and daily metrics through the existing advertising services and must remain unchanged.

### Migration draft scope

The Sprint 4.10 migration draft adds nullable fields to existing `ad_campaigns` and `ad_metrics` only. It is additive, existing-data-safe, downgrade-safe, PostgreSQL-compatible, and independent of live Meta API or token storage. It intentionally does not create `meta_ad_connections`, encrypted token fields, live OAuth tables, production sync jobs, or apply-sync persistence.

### AdCampaign fields added

Nullable `ad_campaigns` fields:

```text
external_source: String(50), nullable=True
external_account_id: String(128), nullable=True
external_campaign_id: String(128), nullable=True
external_status: String(64), nullable=True
external_objective: String(128), nullable=True
last_synced_at: DateTime(timezone=True), nullable=True
sync_source: String(32), nullable=True
```

A non-unique lookup index is drafted first:

```text
ix_ad_campaigns_workspace_external_identity
workspace_id + external_source + external_account_id + external_campaign_id
```

Future uniqueness can be considered only after safe backfill and PostgreSQL runtime QA.

### AdMetric fields added

Nullable `ad_metrics` fields:

```text
source_type: String(32), nullable=True
external_source: String(50), nullable=True
external_account_id: String(128), nullable=True
external_campaign_id: String(128), nullable=True
last_synced_at: DateTime(timezone=True), nullable=True
sync_run_id: UUID, nullable=True, non-FK until meta_sync_runs exists
```

A non-unique lookup index is drafted first:

```text
ix_ad_metrics_workspace_external_identity_date
workspace_id + external_source + external_account_id + external_campaign_id + metric_date
```

### Backfill and runtime gate

Sprint 4.10 does not perform guessed or destructive backfill. New fields remain nullable. Future backfill should classify rows only when safe: manually created rows as `manual`, safely identified imported rows as `csv_import`, and unknown historical rows as `null` until reviewed. Financial formulas, attribution calculations, and import behavior remain unchanged.

The migration remains runtime-gated: static Alembic validation can pass locally, but PostgreSQL upgrade/downgrade/upgrade must be run on a safe non-production database before staging or pilot approval. Advertising import remains not pilot-ready, and Sprint 4.4 runtime/staging blockers remain open.

### Preview compatibility

The read-only preview now prefers exact external identity matching when existing snapshots have `external_source`, `external_account_id`, and `external_campaign_id`. If exact identity is missing, preview falls back to normalized name/platform matching and keeps `NEEDS_EXTERNAL_ID_SUPPORT` context. Ambiguous matches and manual/CSV metric overlaps remain conflicts. Preview remains dry-run only with `db_writes = false`.

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
