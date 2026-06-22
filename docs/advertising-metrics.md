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
