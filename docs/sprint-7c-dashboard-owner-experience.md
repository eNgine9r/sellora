# Sprint 7C — Dashboard Owner Experience

## 1. Scope

Sprint 7C focused on frontend Dashboard owner experience only. No backend analytics engine, Meta feature, database table, or Alembic migration was added.

Goal: make the Dashboard answer what is happening in the Instagram shop, whether the numbers are good or bad, why they look that way, and what the owner should do next.

## 2. Dashboard audit

Dashboard currently uses existing workspace-scoped API/data sources: dashboard summary, sales summary, profit summary, sales trend, top products, advertising summary, orders, leads, inventory summary, shipment summary, products, and variants.

Supported period behavior comes from the existing shared date range provider and existing API query parameters (`date_from`, `date_to`). The Dashboard does not fake periods unsupported by the backend.

Audit findings addressed:

- KPI period context needed to be more visible near the title and KPI cards.
- Recent orders needed clarification because they can be all-time while KPI cards are selected-period.
- Existing alert-like blocks needed clearer action links and data-based explanations.
- Advertising and profit states needed safer missing-data copy.
- Mobile layout needed stacked cards instead of dense desktop-only blocks.

## 3. KPI cards changes

Top KPI cards now focus on owner-facing questions: orders, revenue, net profit, and ROAS/ad spend. Helpers distinguish true zero values from missing data.

Examples implemented:

- Orders show a zero-state helper when no orders exist in the selected period.
- Revenue explains when revenue appears after paid/completed orders.
- Net profit shows `—` with missing-cost guidance when revenue exists but profit cannot be confidently explained.
- ROAS/ad spend explains that advertising metrics require ad spend data.

## 4. Period selector/data context

Selected period is now surfaced in a dedicated context card near the Dashboard title and KPI cards.

Copy explains: metrics are calculated for the selected period; if there were no orders, KPI values may be zero.

The card also explains abbreviations:

- ROAS — окупність реклами
- CPA — ціна замовлення
- AOV — середній чек

## 5. Lead funnel result

Added an owner-facing Sales Funnel block using existing frontend data:

```text
Ліди → Замовлення → Доставлено
```

It shows lead count, order count, delivered order count, and safe conversion percentages only when denominators exist. If there is not enough data, it shows an honest insufficient-data empty state.

No Instagram message count is faked because no active message API exists.

## 6. Orders/fulfillment snapshot result

Added an operational order state snapshot for selected-period orders:

- new orders;
- confirmed orders;
- shipped orders;
- returned/cancelled orders.

The block explains what needs confirmation, shipment, or review and links to Orders.

## 7. Advertising snapshot result

Added a clearer Advertising snapshot with spend, ad orders, CPA, ROAS explanation, and a link to Advertising.

If no advertising data exists for the selected period, the Dashboard now explains that the owner can add manual metrics or import CSV. It does not claim Meta API sync is active.

## 8. Finance/profit snapshot result

Added a Finance and profit snapshot with revenue, net profit, AOV, and a Finance link.

Missing profit data is explained as a data-completeness issue: check product costs, expenses, and advertising data.

## 9. Inventory/alerts result

Added a product/inventory owner block with low-stock, out-of-stock, and stock-unit context. If products are not present yet, it prompts adding products or importing a catalog.

Actionable alerts now include data-based cards for low stock, orders awaiting shipment, missing profit inputs, missing advertising data, and no selected-period activity.

## 10. Recent orders result

Recent orders are intentionally shown from the latest created orders regardless of selected period. The subtitle now says this explicitly so zero KPI values for the selected period are not confused with historical orders.

The recent-orders component keeps desktop table layout and mobile card layout.

## 11. Loading/empty/error states

Dashboard still keeps global loading and error handling. Sprint 7C adds safer block-level empty/missing-data states for funnel, advertising, finance/profit, inventory, and action alerts.

Known follow-up: fully isolated per-block retry controls could be added later if the design system formalizes a dashboard block error component.

## 12. Mobile dashboard QA

Static responsive review completed for 375px, 390px, 430px, and 768px targets:

- KPI cards use responsive grid stacking.
- Owner alerts and funnel blocks stack cleanly.
- Snapshot cards use `min-w-0` and avoid wide tables.
- Recent orders keep mobile card layout.
- Primary action links remain reachable.

Manual browser QA remains recommended before full release approval.

## 13. RBAC/workspace safety

No backend permissions, workspace dependencies, routes, repositories, or services were changed.

Dashboard queries continue to use the current workspace ID through the existing services, and OWNER/MANAGER/ANALYST access behavior remains unchanged.

## 14. Performance notes

No new duplicate API families were added. Sprint 7C reuses existing React Query data already loaded by the Dashboard and derives owner-facing summaries in-memory from existing data.

The Dashboard should show useful content as soon as existing queries resolve and should not require a new backend analytics engine.

## 15. Known limitations

- Sprint 7F runtime PostgreSQL migration QA remains blocked and separate from this frontend-only Dashboard sprint.
- Manual mobile/browser QA is still required for full approval.
- Per-block retry controls are not fully implemented; current behavior relies on existing global refetch/error handling and block-level empty states.
- Instagram message count is not shown because it would require an integration/API that is out of scope.
- No database migration was added in Sprint 7C.

## 16. Final recommendation

**Sprint 7C — CONDITIONALLY APPROVED ⚠️**

Reason: Dashboard owner experience, KPI clarity, funnel, snapshots, data explanations, responsive structure, docs, and regression coverage were improved without backend or migration changes. Full approval should wait for manual browser/mobile QA at 375px, 390px, 430px, and 768px plus the already-known Sprint 7F runtime migration closure.
