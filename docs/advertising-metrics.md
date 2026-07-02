# Advertising Metrics — Sprint 4.0 Source of Truth

Sellora advertising metrics support the MVP manual/import flow today and prepare for a future Meta Ads API sync. Backend/API enum values remain English; Ukrainian/English labels are handled only in the frontend i18n layer.

## Current data sources

1. **Manual entry** in `/advertising` for campaigns and daily metrics.
2. **Import Center advertising import** for historical or recurring spreadsheet reports.
3. **Future Meta Ads sync** is planned but is not active in Sprint 4.0.

Manual and imported values remain first-class. Future API-synced rows must be clearly marked by source and must not overwrite manual/imported rows unless an explicit deduplication rule is implemented.

## Formula definitions

| Metric | Formula | Zero denominator behavior |
| --- | --- | --- |
| Spend | `sum(ad_metric.spend)` | `0` when no rows exist |
| Messages | `sum(ad_metric.messages)` | `0` when no rows exist |
| Leads | `sum(ad_metric.leads)` | `0` when no rows exist |
| Orders | `sum(ad_metric.orders)` | `0` when no rows exist |
| Revenue | `sum(ad_metric.revenue)` | `0` when no rows exist |
| Gross Profit | `revenue - product_cost` when order/product cost data exists | unavailable when cost data is unavailable |
| Net Profit | `sum(ad_metric.net_profit)` or order profit after spend/cost attribution | hidden when role cannot view profit |
| ROAS | `revenue / ad_spend` | `null` / `—` if spend is `0` |
| ROI | `net_profit / ad_spend` | `null` / `—` if spend is `0` |
| CPA | `ad_spend / orders` | `null` / `—` if orders is `0` |
| CPL | `ad_spend / leads` | `null` / `—` if leads is `0` |
| Conversion Rate | `orders / leads` | `null` / `—` if leads is `0` |
| Cost per Message | `ad_spend / messages` | `null` / `—` if messages is `0` |
| CPC | `ad_spend / clicks` | `null` / `—` if clicks is `0` |
| CPM | `ad_spend / impressions * 1000` | `null` / `—` if impressions is `0` |
| CTR | `clicks / impressions` | `null` / `—` if impressions is `0` |

The UI must never render `NaN`, `Infinity`, `undefined`, or raw `null`; it should show `—`, a localized empty state, or a localized restricted state.

## Consistency rules

- `/advertising`, `/dashboard`, `/analytics`, and Import Center reports must use the same period boundaries for comparable metrics.
- Backend advertising aggregate helpers return `null` for unsafe divisions; frontend display components format this as unavailable.
- Financial metrics remain RBAC-sensitive. OWNER and ANALYST can view financial advertising metrics under current rules; MANAGER views operational metrics without owner-only profit fields where restricted.
- All advertising queries and imports must be scoped by `workspace_id` and ignore soft-deleted campaigns/metrics.

## Manual import compatibility

- Daily metrics are unique by campaign and metric date.
- Duplicate imported daily metrics should be skipped, blocked, or updated predictably according to the import flow summary; they must not silently create duplicate rows.
- Imported spend, leads, messages, orders, revenue, and net profit feed the same advertising module and analytics formulas as manually entered values.
- No fake Meta API data should be mixed into manual/imported data.

## Sprint 4.0.1 validation result

Local validation recovered after the Sprint 4.0 dependency outage. Backend `compileall`, full `pytest`, and app import pass; frontend typecheck/build pass; advertising regression markers pass. Manual staging verification still requires staging credentials and synthetic advertising data before Sprint 4.0 can be fully approved for pilot operations.

## Sprint 4.1 Manual Advertising Import QA Scenario

Use synthetic data only for QA. Do not upload real Meta exports, real campaign identifiers, customer data, private order data, tokens, app secrets, business IDs, or ad account IDs.

Recommended synthetic row:

| Field | Value |
| --- | --- |
| Campaign | DEMO Meta Campaign |
| Platform | META |
| Date | Current safe test date |
| Spend | 1000 UAH |
| Messages | 50 |
| Leads | 20 |
| Orders | 5 |
| Revenue | 5000 UAH |
| Net Profit | 1500 UAH |

Expected values for the same selected period:

| Metric | Formula | Expected value |
| --- | --- | --- |
| ROAS | revenue / spend | 5.0 |
| CPA | spend / orders | 200 UAH |
| CPL | spend / leads | 50 UAH |
| ROI | net_profit / spend | 1.5 |
| Cost per Message | spend / messages | 20 UAH |
| Conversion Rate | orders / leads | 25% |

Advertising import dry-run should explain which rows will create, update, or skip daily metrics. Duplicate campaign/date rows are expected to update predictably or produce a clear duplicate warning, depending on the import path used. Row-level errors must include the row number and a non-technical reason that a shop owner can fix in the spreadsheet.

Column aliases supported for advertising QA include common English and Ukrainian names such as `campaign`, `campaign_name`, `кампанія`, `назва кампанії`, `platform`, `платформа`, `date`, `дата`, `spend`, `витрати`, `рекламний бюджет`, `messages`, `повідомлення`, `leads`, `ліди`, `orders`, `замовлення`, `revenue`, `дохід`, `виручка`, `net_profit`, `чистий прибуток`, `impressions`, `покази`, `clicks`, and `кліки`.

Dashboard, Analytics, and `/advertising` must use the same period boundaries and the same daily ad metrics source. Zero denominators are displayed as `—`, never `NaN`, `Infinity`, `undefined`, or raw `null`.

## Campaign Attribution Current Behavior

Campaign attribution remains intentionally optional for MVP. Leads currently use lead source, orders can store ad cost, and advertising campaign metrics remain workspace-scoped manual/import records. Existing leads and orders without a campaign remain valid. Future Meta Ads attribution will map campaign/ad identifiers after official Meta API integration is designed and approved.

## Sprint 4.2 Pilot Template Dataset

Sprint 4.2 adds a pilot-safe CSV import template in `docs/templates/advertising-import-template.csv`. The same CSV file is available in the frontend at `/templates/advertising-import-template.csv` for pilot download and direct staging upload.

The synthetic demo rows are:

| Campaign | Platform | Spend | Messages | Leads | Orders | Revenue | Net Profit | Impressions | Clicks | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| DEMO Meta Campaign — Watches | META | 1000 | 50 | 20 | 5 | 5000 | 1500 | 10000 | 300 | Non-zero ROAS/CPA/CPL |
| DEMO Instagram Campaign — Rings | INSTAGRAM | 750 | 35 | 15 | 3 | 2700 | 800 | 7000 | 180 | Non-zero ROAS/CPA/CPL |
| DEMO Retargeting Campaign | META | 500 | 20 | 8 | 2 | 1800 | 450 | 4000 | 90 | Non-zero ROAS/CPA/CPL |
| DEMO Zero Leads Campaign | INSTAGRAM | 250 | 12 | 0 | 0 | 0 | 0 | 2500 | 60 | Zero-denominator QA row |

The zero-denominator row must show `—` for CPA/CPL/conversion rate and must never show `NaN`, `Infinity`, `undefined`, or raw `null`.

## Sprint 4.3 Campaign Decision Support

Sprint 4.3 adds frontend-computed campaign insights on `/advertising` without changing backend/API enum values or persistence. The comparison uses existing workspace-scoped campaign performance aggregates for the selected period and keeps manual entry / CSV import as the active MVP data source.

Decision statuses are deterministic UI labels:

| Status | Ukrainian label | Rule summary | Owner action |
| --- | --- | --- | --- |
| `GOOD` | Добре працює | Spend exists and ROAS is at least `4.0`. | Consider scaling after checking stock and order capacity. |
| `WATCH` | Потрібно спостерігати | Leads exist without orders, CPA is materially above average, or data is mixed but not clearly profitable. | Review targeting, offer, creative, and lead follow-up. |
| `PROBLEM` | Потребує уваги | Spend exists but orders are `0`. | Pause or investigate before adding more budget. |
| `NO_DATA` | Недостатньо даних | Spend is missing or `0`, so a recommendation would be misleading. | Add manual/CSV metrics for the period first. |

Top Campaigns sort by ROAS, then revenue, then orders. Campaigns Needing Attention prioritize `PROBLEM` before `WATCH`, then higher spend/CPA. Unsafe divisions still render as `—`, never `NaN`, `Infinity`, `undefined`, or raw `null`.

## Sprint 4.3.1 Decision Rule Priority and NO_DATA Visibility

Sprint 4.3.1 keeps decision statuses as frontend-computed UI labels, not backend/API enums. The approved rule priority is `NO_DATA → PROBLEM → GOOD → WATCH`.

Detailed priority:

1. `NO_DATA`: campaign has no metric rows, spend is missing, or spend is `0`. Campaigns without metrics are still visible in the comparison table with `Недостатньо даних` / `Not enough data`; unavailable values render as `—`.
2. `PROBLEM`: spend exists and orders are `0`. If `spend > 0, leads > 0, orders = 0`, the precise message is: `Ліди є, але замовлень немає — перевірте обробку Direct або пропозицію.`
3. `GOOD`: ROAS is at least `4.0` and the campaign has positive orders and revenue.
4. `WATCH`: CPA is more than 25% above average, conversion is weak after leads and orders exist, or metrics need review before scaling.

`NO_DATA` rows are excluded from Top Campaigns and Campaigns Needing Attention, but they remain visible in the comparison table so newly created campaigns do not disappear silently. Top Campaigns still sort by ROAS, revenue, and orders. Campaigns Needing Attention still prioritize `PROBLEM` before `WATCH`, then higher spend and CPA. Zero-denominator values must continue to render as `—`, never `NaN`, `Infinity`, `undefined`, or raw `null`.

## Sprint 4.5 Reporting Consolidation Formula Gate

Sprint 4.5 keeps `/advertising` as an owner-facing report built from manual entry and CSV-imported advertising metrics. The page is ordered around source/status, summary KPIs, campaign decision support, manual attribution clarity, campaign comparison, daily metrics, trend details, import help, and the pilot readiness gate.

### Final MVP formula definitions

| Metric | Source | Formula | Safe empty value |
| --- | --- | --- | --- |
| ROAS | Imported/manual ad metrics | `total_revenue / total_spend` | `—` when spend is `0` |
| ROI | Imported/manual ad metrics | `total_net_profit / total_spend` as a percent where profit is visible | `—` when spend is `0` or profit is restricted |
| CPA | Imported/manual ad metrics | `total_spend / total_orders` | `—` when orders are `0` |
| CPL | Imported/manual ad metrics | `total_spend / total_leads` | `—` when leads are `0` |
| Cost per Message | Imported/manual ad metrics | `total_spend / total_messages` | `—` when messages are `0` |
| Conversion Rate | Imported/manual ad metrics | `total_orders / total_leads` | `—` when leads are `0` |
| Attributed Revenue | Manual lead/order campaign attribution | Sum of revenue for orders where `campaign_id` was manually selected and the selected period includes the order | `—` when no linked orders exist or runtime QA is unavailable |
| Attributed Net Profit | Manual lead/order campaign attribution | Sum of net profit for orders where `campaign_id` was manually selected and profit is visible to the role | `—` when no linked orders exist, profit is restricted, or runtime QA is unavailable |
| Attributed Orders | Manual lead/order campaign attribution | Count of orders where `campaign_id` is set | `0` when no linked orders exist |
| Unattributed Orders | Manual lead/order campaign attribution | Count of valid orders in the selected period where `campaign_id` is empty | `0` when all orders are attributed |
| Linked Campaigns | Manual lead/order campaign attribution | Count of distinct workspace campaigns linked to at least one lead/order in the selected period | `0` when no campaigns are linked |

Manual attribution metrics are separate from imported/manual ad metric totals. Imported advertising rows answer how campaigns performed according to uploaded or manually entered ad reports; lead/order attribution answers which CRM orders were manually linked to campaigns. Orders without a campaign remain valid and must not be shown as errors.

The UI and docs use the same zero-denominator rule: `null` values render as `—`, and Sellora must not render `NaN`, `Infinity`, `undefined`, or raw `null` in advertising reporting.

### Pilot readiness gate

The `/advertising` page now includes a visible but non-alarming status block. It lists manual metric entry, CSV template import, ROAS/CPA/CPL, campaign guidance, and manual order-to-campaign attribution as available MVP capabilities. It also keeps staging import QA, PostgreSQL runtime migration validation, and browser/mobile QA as pending validation items. Meta Ads API remains future work and is not active.

Advertising import is still not pilot-ready until deployed staging import QA passes with synthetic data. Sprint 4.4 attribution is still not fully approved until PostgreSQL runtime migration QA and browser/mobile attribution QA are completed.

## Sprint 4.6 — Meta Ads readiness boundary

Meta Ads API remains future work and is not active. Manual entry and CSV import remain the current MVP advertising data source.

Future Meta read-only sync may import campaign delivery metrics such as spend, impressions, reach and clicks. Orders, revenue and net profit remain Sellora-side business metrics unless a separate Conversions API sprint is implemented after legal/privacy review.

Manual/import rows and future Meta-sourced rows must not silently overwrite each other. Future sync source and external ID fields should be additive, workspace-scoped, and clearly displayed in UI before any automated merge behavior exists.

Advertising import remains not pilot-ready until staging CSV import QA passes. Sprint 4.4 attribution remains conditional until PostgreSQL runtime migration QA and browser/mobile attribution QA pass.

## Sprint 4.7 — Fake Meta sync simulation metrics

The fake Meta sync simulation is backend-only and dry-run only. It can produce candidate delivery metrics: spend, impressions, clicks, messages, and leads. It intentionally does not provide Sellora orders, revenue, or net profit from Meta.

Future Meta-sourced daily metrics must use an idempotent identity equivalent to `workspace_id + external_source + external_campaign_id + metric_date`. Manual/import rows and future Meta rows must not silently overwrite each other. Zero spend, zero clicks, missing leads, and no-data campaigns must continue to render safely as `—` or structured no-data states rather than `NaN`, `Infinity`, `undefined`, or raw `null`.

## Sprint 4.8 — Sync preview conflict policy

Meta sync preview is read-only. It compares fake Meta delivery candidates against current Sellora campaigns/metrics and returns `WOULD_CREATE`, `WOULD_UPDATE`, `WOULD_SKIP`, `POTENTIAL_CONFLICT`, `NEEDS_EXTERNAL_ID_SUPPORT`, or `INVALID` preview classifications without persisting them as backend/API enums.

Manual/CSV data is protected by default. If a future Meta row overlaps an existing manual/CSV row, preview must flag `POTENTIAL_CONFLICT` and must not overwrite spend, impressions, clicks, messages, leads, orders, revenue, or net profit. Orders, revenue, and net profit remain Sellora-side metrics and are not imported from Meta Ads Insights.

Because exact external IDs are not persisted yet, preview includes an external ID limitation note. Future schema work still needs additive `external_source` / `external_campaign_id` support before live sync can write rows safely.

## Sprint 4.9 — External identity and source separation design

Sprint 4.9 designs future source separation without changing the database. Future `ad_campaigns` should receive nullable external identity fields such as `external_source`, `external_account_id`, `external_campaign_id`, `external_status`, `external_objective`, `last_synced_at`, and `sync_source`. Future `ad_metrics` should receive nullable source fields such as `source_type`, `external_source`, `external_account_id`, `external_campaign_id`, `last_synced_at`, and `sync_run_id`.

Future Meta metric idempotency should use `workspace_id + external_source + external_account_id + external_campaign_id + metric_date`. Manual/CSV data is protected by default: Meta-owned rows can update only Meta-owned rows with the same external identity, while overlapping manual or CSV rows are conflicts.

Orders, revenue, and net profit remain Sellora-side business metrics. Meta Ads Insights may provide spend, impressions, clicks, and messages/leads where available, but it must not overwrite manual/CSV business outcomes or import Sellora profit. Conversions API remains a separate future sprint that requires legal/privacy review.

## Sprint 4.10 — Runtime-gated source fields

Sprint 4.10 drafts nullable source/external identity fields for future Meta separation without changing formulas or importing Meta business outcomes. `ad_campaigns` now has nullable model/migration draft fields for external identity and `sync_source`; `ad_metrics` now has nullable fields for `source_type`, external identity, `last_synced_at`, and nullable `sync_run_id`.

Manual/CSV rows remain protected and valid with null source fields until a safe backfill is approved. Meta-owned rows may be matched by exact external identity in preview, but preview remains dry-run and no DB sync writes are added. Orders, revenue, and net profit remain Sellora-side metrics.

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
