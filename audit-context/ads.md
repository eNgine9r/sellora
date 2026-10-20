# Advertising, attribution and finance context

Date: 2026-10-19. Scope: source-only, no provider calls, database queries, customer actions or runtime environment reads. This is a context map, not a live-data or production correctness certification.

## Capability map

| Capability | Implementation evidence | Boundary |
|---|---|---|
| Campaign CRUD, daily metric CRUD | `backend/app/services/advertising_service.py:31-131`; repository `advertising_repository.py:13-57` | Workspace scoped, soft deletion, critical writes audited. One metric per campaign/date. |
| Advertising summaries, campaign performance, trends | `advertising_service.py:134-186,196-268` | Sums stored AdMetric values including manually supplied orders/revenue/net_profit. Does not join CRM orders. |
| Nullable manual campaign attribution | `models/lead.py:30`, `models/order.py:39`; `order_service.py:63-90,332-334`; `lead_service.py:195-197` | Campaign association exists; source/evidence/confidence/touch history does not exist on these references. |
| Integrated order creation accepts campaign | `order_fulfillment_service.py:478-494` | Caller supplies campaign_id. No automatic referral mapping in this path. |
| Dashboard advertising report | `analytics_service.py:315-390`; `analytics_repository.py:78-91` | Separate aggregation implementation, again AdMetric based; excludes deleted campaigns. |
| Meta Ads discovery/preview | `api/v1/meta_ads.py:69-97`; `meta_ads_sync_preview_service.py:24-25,39-50,87-128` | Routes instantiate default fake read-only client; preview explicitly writes no campaign/metric rows. |
| Live read-only Ads adapter | `integrations/meta_ads/live_read_only_client.py:49-155` | Adapter exists. Search of backend/app found its class definition and error imports, no runtime construction. |
| Meta staging validator | `meta_ads_staging_validation_service.py:35-114` | Defaults to fake client at L81 even after encrypted token checks. Response reports mode=fake. |
| Real Instagram messages to Direct | `meta_instagram/services/inbound_message_service.py:47-167` | Deduplicated provider messages, profile/customer intent enrichment. Message projection retains text/media/postback-presence, not ad referral. |
| Order finance | `profit_calculation_service.py:49-91`; `finance_service.py:143-225` | New/confirmed/shipped/delivered/completed orders included unless refunded; returned/cancelled excluded. Order allocated ad costs drive finance, not total campaign spend. |
| Finance completeness | `finance_service.py:149-216` | Explicit warnings for manual data, spend allocation mismatch, missing product/delivery costs, refunds/discounts. |

## Cross-cutting rules and facts

- Honest separation already exists in copy: manual/import data is active and Meta sync is future (`frontend/src/app/advertising/page.tsx:100,108,111,116`). The summaries themselves do not measure confirmed Direct sales by following the lead/order links (`advertising_service.py:196-228`).
- Manual metrics store all funnel/result fields with zero defaults; external identity/provenance columns are nullable (`models/ad_metric.py:15-33`). A zero stored order count alone does not establish that all Direct orders were recorded.
- Lead/order campaign IDs are validated against a workspace-scoped, undeleted campaign (`advertising_repository.py:21-23`). Unknown attribution remains representable as null.
- Ordinary Advertising totals include undeleted metrics without excluding a soft-deleted campaign (`advertising_repository.py:64-76`); Analytics report joins and excludes deleted campaigns (`analytics_repository.py:78-91`). These are different inclusion contracts.
- Date basis: ad reports use metric_date; order reports use completed_at falling back to created_at (`analytics_repository.py:26-38,78-91`, `finance_repository.py:22-34`). No attribution cohort/window model found in reviewed source.
- Finance ad_spend sums order.ad_cost while campaign spend is compared only for a warning (`finance_service.py:177-185`). Returned/cancelled/refunded orders lose all canonical components, including their ad/delivery costs (`profit_calculation_service.py:67-83`); actual return/refund expenses require manual adjustments (`finance_service.py:203-220`).
- All Ads module reads require backend Analyst minimum and writes Owner (`api/v1/advertising.py:35-120`). Meta start/callback/disconnect require Owner; read-only preview requires Analyst (`api/v1/meta_ads.py:42-118`).

## UI density and data flow

`frontend/src/app/advertising/page.tsx:64-68` fires five parallel queries. Summary/performance/trend each independently load the period's AdMetric rows. Campaigns and metrics are loaded completely and client-paginated (L85-95); performance defaults to 10 server rows (`services/advertising.ts:13`) before client pagination.

The page presents source banner, Meta readiness, KPI helpers, four formula/import/source cards, insights, manual attribution explanation, performance table, metrics table, trend, campaign table and a readiness gate (L99-116). Source/formula/readiness explanations repeat. The performance table has 12 columns and minimum width 920px (`campaign-performance-table.tsx:10-16`). No table empty/loading/error branch exists there; page passes empty arrays during loading/failure (page L112-114). Date inputs have empty initial values and English aria labels (`advertising-date-range-filter.tsx:1`), while backend defaults to a 31-day inclusive UTC range (`advertising_service.py:189-193`).

## Unenforced assumptions / nothing found

1. Reported AdMetric.orders/revenue reflect all actual Direct orders: **nothing found**. Values are accepted as metrics and aggregated; CRM campaign links are not consulted.
2. A known Instagram ad referral survives into CRM order attribution: **nothing found**. Inbound projection ignores referral and models have no touch/ad evidence fields.
3. A preview-ready Meta connection proves live Ads delivery data is fetched: **nothing found**. Default services use deterministic fake clients; live adapter is unwired in reviewed route graph.
4. A current order-level net profit equals whole-shop realized net profit: **nothing found**. Included statuses contain NEW and CONFIRMED, and allocated ad cost can differ from total spend; existing warnings describe this.
5. Unavailable/partial conversion input is distinguished from a true zero for campaign decisions: **nothing found**. `decision-support.ts:83-106` marks positive spend/no orders as PROBLEM; it has no data-completeness or attribution-coverage input.

## Open questions for product/implementation phase

- Should reports default to created-order cohort, completed revenue period, or show both clearly? How should paid, COD pending collection, delivered, returned and refunded be distinguished?
- What real referral payloads does this Meta Instagram product deliver for the connected account? No provider documentation or live events were inspected in this source-only pass.
- Should repeat purchases stay attributed to their original ad, latest known touch, or explicit manager choice? No accepted attribution window/policy found.
- How should manual campaign linkage be inherited from lead to order? Lead-to-customer conversion preserves status/audit but no customer/campaign relation at `lead_service.py:122-157`; other Direct paths require separate workflow audit.
- Have source_type/external identity migration and sync-conflict handling been exercised against a safe PostgreSQL test instance? Prior docs describe historical blockers; current live DB state was intentionally not read.
- Should historical metrics remain in ordinary Advertising after campaign archival? Current two report paths differ.

Function records: `functions/ads-summary.md`, `functions/ads-meta-preview.md`, `functions/ads-profit-components.md`, `functions/ads-referral-projection.md`.

## Bounded implementation handoff (proposal after context mapping)

First deliver a separate, honest CRM campaign-sales report using existing columns; do not repurpose existing declared metrics or enable fake/live Meta preview as production sync.

- Add GET /advertising/crm-attribution in `api/v1/advertising.py`, mirroring Analyst read RBAC and backend-derived workspace context.
- Add response types in `schemas/advertising.py`: selected start/end dates, date_basis=order_created_at, source=crm_manual_campaign_link, total/new/open/delivered/paid/returned/cancelled/refunded counts, attributed/unattributed counts, campaign rows including archived labels, and explicit data completeness notes.
- Add `AdvertisingAnalyticsService.crm_attribution` and `AdvertisingAnalyticsRepository.group_crm_orders`. Aggregate in SQL by campaign/status/payment, with Order.workspace_id/deleted_at and inclusive UTC created_at boundaries. Do not reuse `AnalyticsRepository.list_orders` unchanged: its completed_at fallback moves existing orders between periods.
- Join campaigns with campaign.workspace_id=current workspace; retain soft-deleted/archived campaign history rather than silently changing historical totals. Null/unresolved attribution is a visible unknown bucket. Do not infer attribution from username/text.
- Keep AdMetric-reported spend/orders/revenue under their own source labels; show separate CRM counts. Preserve report rows with CRM orders and no metric spend, and campaigns with spend and no CRM orders. Source disagreement is a meaningful state.
- Treat NEW/CONFIRMED/SHIPPED values as order pipeline. DELIVERED/COMPLETED and payment!=REFUNDED identify delivered current sales, while PAID is a separate payment fact; COD alone is not collection evidence. Cancellation, return and refund are shown explicitly and do not count as current successful sales. Counts may overlap unless defined as a partition; document the choice.
- Reuse `ProfitCalculationService.REVENUE_STATUSES/includes_order` for any canonical estimated/order-derived economics without silently relabeling them realized. Initial CRM sales report can omit profit until cost completeness/allocation semantics are exposed. Campaign total spend must not be subtracted again from already allocated order profit.
- Avoid a first-phase causal ROAS claim: current-period CRM created orders and same-period campaign spend do not form a complete attribution cohort. Existing declared-data ROAS can remain clearly labelled. Zero denominator stays null.
- Collapse repeated source/formula/readiness text into one concise source/status area and optional details. Provide visible query loading/error/retry/empty states before presenting conclusions. Keep mobile cards for campaign outcomes and expandable detailed metric columns.

Suggested meaningful tests: extend fake repository style from `tests/test_advertising.py:83-123`; use synthetic orders with null campaign, archived campaign, cross-workspace reference, declared-vs-CRM mismatch, no-spend sales, no-sale spend, all order/payment states, UTC midnight boundaries and completion date outside creation period. Assert no double-counting, no writes and no borrowed counts from AdMetric.orders. Repository tests should execute query against safe test DB where available to verify workspace/soft-delete/join/date inclusion rather than only trusting a filtering fake. Preserve existing advertising/profit/finance/analytics suites.

Later separately scoped work: provider-verified referral evidence capture and touch history, idempotent actual Ads delivery import with external identity/source conflict rules, attribution-policy confirmation, and cost/refund reconciliation. These need provider contracts and possibly migrations; they are not established by this source-only pass.
