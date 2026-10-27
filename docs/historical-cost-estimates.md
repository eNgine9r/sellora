# Historical cost estimates — advisory snapshots (October 2026)

## Product decision

Imported archive/TТН records may have an estimated landed product cost when the sold SKU, payment, or order amount is unknown. It must never be treated as confirmed product cost or profit.

The Your Jewelry shop owner confirmed historical spreadsheet formula: **selling amount (F) − half-net profit (G) = landed procurement cost + delivery from China**. Advertising is NOT included and should be tracked separately. Do not subtract shipping from China a second time through the buyer shipping field.

The external reconciliation report has 607 archived TТН records and 22 unique May 2026 row matches by date, city and full selling amount. Those matches do not prove payment or exact product identity. Never turn an estimated cost into recorded revenue or paid status automatically.

## Storage, service and API

Alembic revision 202610230043 adds nullable fields to orders:

- **estimated_product_cost**: strictly positive Decimal(12,2), or null.
- **estimated_cost_source**: SHEET_ROW_MATCH, PRICE_MEDIAN, PRICE_BAND, or MANUAL.
- **estimated_cost_confidence**: MULTI_SIGNAL_MATCH, PRICE_ONLY, LOW, or MANUAL_REVIEW; the server derives it from source, not the caller.
- **estimated_cost_reference**: optional 512-char source URL/row; required for SHEET_ROW_MATCH.

Endpoints:

- PUT /api/v1/orders/{order_id}/estimated-cost, body containing positive amount, enum source, and optional source reference.
- DELETE /api/v1/orders/{order_id}/estimated-cost clears only the advisory estimate.

Both endpoints require an authenticated MANAGER or OWNER, workspace isolation and row locking. They reject non-historical orders and orders with confirmed product cost, and produce audit log events. They do not modify order items, item cost snapshots, confirmed COGS, payment, revenue, net profit, status, inventory or advertising.

SHEET_ROW_MATCH indicates a *multi-signal match*, not a confirmed bank transaction.

## UX and localization

Open Orders, choose an imported historical order without confirmed product cost, and use the separate estimated cost card. Analysts can view; managers and owners can edit or clear estimates. Ukrainian is the primary locale, English is supported, backend enums stay English. Clearly show unverified status, method, confidence and source.

Keep estimated amounts out of normal finance KPIs, reports and ROAS. Any future estimated-profit analytics must be opt-in and visibly separated from confirmed P&L.

## Release safety

1. Review/test code and SQL migration.
2. Apply Alembic migration before deploying the backend and frontend that read the added columns.
3. Smoke test MANAGER/ANALYST RBAC, cross-workspace access, create/update/clear API and mobile order details.
4. Back up the current financial records. Load reviewed source matches using the dedicated API only, with dry-run and audit. No automatic mass writes are performed here.
5. Verify the existing 484 historical orders with confirmed costs, 607 with missing costs, normal orders, P&L and stock are unchanged.

Before migration downgrade, export the advisory estimates; downgrade drops those four columns and their data.
