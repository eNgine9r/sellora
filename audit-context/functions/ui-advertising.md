## AdvertisingPage in frontend/src/app/advertising/page.tsx (L41-L126)

**Purpose:** Manual/import advertising metrics, campaign management and period performance reporting.

**Inputs & Assumptions:**
- Auth workspace/role L44-L45,L62-L63; only OWNER gets mutation controls.
- Semi-trusted campaign/metric/result API data. API source semantics delegated domain audit.
- Date strings initial blank represent allperiod; summary/performance/trend include dates L66-L68; daily metrics remain allperiod L65.
- Assumes displayed daily rows and summary period understood; date-specific table separation not established in this component.

**Outputs & Effects:**
- Queries campaigns, daily metrics, summary, performance, trend L64-L68.
- Mutations create/update/archive campaign or create/update/delete metrics L78-L83.
- Per-table client pagination L85-L95; destructive confirmation L120-L121.

**Block-by-Block:**
- L64-L70: establishes five queries, readiness copy arrays including technical QA/migration status.
- L71-L83: mutation cache invalidation; campaign/metric destructive actions delegated server.
- L99-L109: header, manual-source banner, period filter, Meta readiness, KPI row, import/formula/source cards.
- L110-L116: insights, another manual-attribution explanation, performance table, daily table, trend, campaign table, engineering readiness section.
- L118-L123: dialogs/forms/confirmations and errors. General query-level loading/error panel not found in the audited page JSX.

**Cross-Function Dependencies:**
- services/advertising.ts (source inspected L5-L14): dates encoded for summary/performance/trend; fetchAdMetrics has no date arguments.
- CampaignPerformanceTable (source inspected L7-L18): 920px table, 12columns, no mobile cards or empty branch.
- CampaignInsightsPanel/AdMetricTable/MetaAdsReadinessCard: render helpers imported; their backend formula/source contracts not traced here.
- Shared CompactSummary/WorkspaceSplitView/EntitySidePanel (source inspected crm-workspace.tsx L48-L82): semantic surfaces and responsive panel foundation.
- Backend aggregation: delegated domain audit; do not relabel API counts as actual CRM sales until source known.

**Open Questions:**
- Which summary fields derive from manually entered daily metrics and which campaign-performance fields derive from linked actual orders? Parent domain audit must resolve before consolidation.
- Can selected period consistently filter daily metrics without changing API contract (client date filtering) and communicate source?
- Should readiness details move to integration settings/collapsed disclosure, preserving truth about unavailable sync?
- Verify responsive campaign cards/table switch at375/390/1280/1440 using synthetic data, no real ad/customer screenshots.
