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
