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
<<<<<<< HEAD
=======

## Manual attribution MVP — Sprint 4.4

Sellora now supports manual campaign attribution for leads and orders. Store owners can optionally select an advertising campaign when a lead or order is created or edited; the link is used only to answer the MVP question: which manually linked campaign led to orders, revenue, and profit.

Rules:

1. Attribution is manual and optional.
2. Leads and orders without a campaign remain valid and are not treated as errors.
3. Campaign links are workspace-scoped; cross-workspace campaign links must be rejected by backend validation.
4. Attribution does not change order revenue, profit, inventory reservation, payment, shipment, or status behavior.
5. The `/advertising` attribution panel counts only orders where a campaign was manually selected.
6. Unattributed orders are shown separately so owners can see what still needs manual attribution.
7. Future Meta attribution may use external campaign/ad identifiers, but Meta API attribution remains future work.
8. Advertising import remains not pilot-ready until deployed manual staging QA passes.
>>>>>>> origin/codex/2026-07-01-create-initial-sellora-repository-structure
