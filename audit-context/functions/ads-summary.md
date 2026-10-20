## AdvertisingAnalyticsService.summary in backend/app/services/advertising_service.py (L138-L140)

**Purpose:** Produces Advertising KPI totals for an optional date period from stored daily advertising metrics.

**Inputs & Assumptions:**
- workspace_id: trusted server context from get_workspace_id; route requires Analyst minimum (`api/v1/advertising.py:L109-L111`).
- Dates: semi-trusted optional date parameters parsed by FastAPI. Missing endpoints resolved from current UTC date (`advertising_service.py:L189-L193`).
- include_sensitive: backend role-derived OWNER/ANALYST check (`api/v1/advertising.py:L31-L32`).
- Completeness of manually reported orders/revenue/profit: **nothing found**. Request schema accepts these fields with defaults (`schemas/advertising.py:L52-L63`).

**Outputs & Effects:** Read-only summary response. No persistence, inventory, customer messages or provider requests.

**Block-by-Block:**

```python
# L139-L140
start, end = resolve_date_range(start_date, end_date)
return summary_from_metrics(self.repository.list_metrics(workspace_id, start, end), include_sensitive)
```

- **What:** Resolves period, loads workspace metrics, calculates totals/ratios.
- **Why here:** Repository receives concrete date boundaries before fetching.
- **Assumes:** Stored metrics are suitable for advertising measurement; no automatic reconciliation to CRM orders is performed.
- **Establishes:** All selected metrics belong to workspace and are undeleted, metric_date within inclusive dates (`advertising_repository.py:L64-L76`).
- **Depended on by:** Summary cards, ratios and campaign decision UI.

**Cross-Function Dependencies:**
- resolve_date_range internal (L189-L193): today UTC fallback; start defaults end minus 30 days. It does not reject reversed dates.
- AdvertisingAnalyticsRepository.list_metrics internal (repository L64-L76): workspace/soft-delete/date filtering, selectinload campaign; does not filter campaign.deleted_at.
- summary_from_metrics internal (L210-L228) calls aggregate (L196-L207), which sums AdMetric fields; no Order/Lead reads.
- safe_div/percent_div/quantize internal (L257-L272): Decimal math with ROUND_HALF_UP to 2 decimals; zero denominator returns None.
- include_sensitive masks net_profit and ROI only (L221,L228); total revenue/orders remain visible.
- Callers: GET /advertising/summary; five separate frontend queries share related source data (`frontend/src/app/advertising/page.tsx:L64-L68`).

**Open Questions:**
- Is date-order validation intended centrally? Not present in this service/route.
- Why does Analytics advertising_report exclude deleted campaigns while this path retains their metrics? See `analytics_repository.py:L78-L91`.
- Can users distinguish imported/reported order counts from CRM-confirmed campaign order counts? Response has no such source split (`schemas/advertising.py:L103-L119`).
