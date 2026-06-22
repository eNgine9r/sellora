# Sellora Staging QA Checklist

Use this checklist for manual staging smoke testing before accepting MVP changes. Keep all credentials, tokens, workspace identifiers, private customer data, and screenshots with sensitive information out of issues, docs, logs, and pull request comments.

## Auth

- Open the public landing page at `/` and verify it does not redirect to login.
- Open `/login`, sign in with a staging test account, and confirm the app redirects to `/dashboard`.
- Reload `/dashboard` and confirm the session restores without asking for a token or workspace ID.
- Let the access token expire during a staging session, reload the page, and confirm refresh-token recovery keeps the user signed in when refresh is valid.
- Use Log out and confirm the session is cleared and private routes redirect to `/login`.

## CRM

- Create a lead with synthetic test data.
- Convert a lead to a customer.
- Add a customer note.
- Add a customer tag.
- Add a customer address.

## Catalog

- Create a product.
- Create a product variant.
- Verify inventory is created for the variant.
- Perform a stock-in transaction.
- Verify low-stock indicators appear when stock is below the configured minimum.

## Orders

- Create an order with synthetic products and customer data.
- Verify inventory reservation occurs.
- Move the order to shipped.
- Complete the order.
- Cancel a separate test order.
- Return a separate test order and verify inventory restoration through the order workflow.

## Advertising

- Create a campaign with synthetic data.
- Add daily metrics.
- Verify CPA and ROAS calculations.
- Verify manager users cannot see net profit or ROI values.

## Shipments

- Create a shipment linked to a test order.
- Mark the shipment in transit and verify the order status updates correctly.
- Mark a shipment delivered and verify the order status updates correctly.
- Mark a shipment returned and verify the order status and inventory behavior follow the order return workflow.

## Import Center

- Upload an Excel file with synthetic staging data only.
- Run mapping suggestions.
- Preview the mapped rows.
- Run a dry run.
- Review validation issues and the import report.
- Execute the import only when the report is acceptable.

## Mobile

- Check `/login`, `/dashboard`, `/leads`, `/customers`, `/orders`, `/products`, `/inventory`, `/shipments`, `/advertising`, `/analytics`, and `/settings/import` at mobile width.
- Verify the sidebar opens as a drawer and closes cleanly.
- Verify cards stack vertically without horizontal page overflow.
- Verify tables either become cards or stay inside controlled horizontal scroll containers.
- Verify forms and dialogs fit phone screens and primary buttons remain touch-friendly.

## Real Product Catalog Import QA

1. Login.
2. Open `/settings/import`.
3. Upload a private product catalog template from local storage.
4. Select `your_jewelry_product_catalog_v1`.
5. Click Suggest mapping.
6. Preview rows.
7. Run dry-run.
8. Review product, variant, inventory, and image counts.
9. Review sample warnings and errors.
10. Import a small private test subset first when possible.
11. Verify `/products`.
12. Verify variants are available in selects.
13. Verify `/inventory`.
14. Create a test order from an imported variant.
15. Verify dashboard still loads.
16. Confirm no private business data is exposed in UI, docs, logs, screenshots, or tests.

## MVP Edit Flow QA

- Edit a lead name/status/notes and confirm the list refreshes.
- Edit a customer name/phone/city and confirm customer details still load.
- Edit a product SKU/name/category/brand/status and confirm variants and inventory are preserved.
- Edit a product variant SKU/color/size/price/barcode/status and confirm duplicate SKUs are rejected.
- Adjust inventory with a stock transaction, then update incoming and minimum quantity.
- Edit order safe fields only: payment status, costs, and notes; keep status changes through status actions.
- Edit shipment tracking/carrier/recipient/city/warehouse/cost fields; keep status changes through shipment status actions.
- Edit an advertising campaign budget/status/date/notes.
- Edit an advertising metric spend/counts/revenue/profit and confirm duplicate campaign/date is rejected.
- Verify an analyst account cannot perform edit mutations.
- Re-check create flows, Import Center dry-run/import, dashboard loading, and workspace header behavior after edits.

## Edit Action Discoverability QA

- Leads: open `/leads`, find a lead row, click **Edit lead**, save a safe field, and verify the list refreshes.
- Customers: open `/customers`, find a customer row, click **Edit customer**; also select a customer and use the detail-panel **Edit customer** button.
- Products: open `/products`, find a product row, click **Edit product**, and verify variants and inventory remain linked.
- Variants: open `/products`, scroll to **Manage product variants**, find a variant row, click **Edit variant**, and confirm the create/edit variant dialog does not overflow on desktop or mobile.
- Inventory: open `/inventory`, use row **Edit thresholds** for incoming/minimum values, then use the transaction form **Adjust stock** for stock corrections.
- Orders: open `/orders`, find an order row, click **Edit order**, and edit only the safe cost/payment/notes fields.
- Shipments: open `/shipments`, find a shipment row or mobile card, click **Edit shipment**, and keep status changes separate from editing.
- Advertising campaigns: open `/advertising`, use the campaigns table **Edit campaign** action.
- Advertising metrics: open `/advertising`, use the daily metrics table **Edit metric** action.
- RBAC: verify OWNER and allowed MANAGER accounts see permitted edit actions, while ANALYST users see read-only states or no edit action.

## Delete / Archive Test Data Cleanup QA

- Leads: `/leads` → row → **Archive lead** → confirm; converted leads should warn that customer records are not deleted.
- Customers: `/customers` → row or detail panel → **Archive customer** → confirm; existing orders and shipments must remain available historically.
- Products: `/products` → product row → **Archive product** → confirm; product disappears from active catalog lists/selects while historical orders remain unchanged.
- Variants: `/products` → **Manage product variants** → row → **Archive variant** → confirm; variants with reserved inventory should be rejected until related orders are resolved.
- Inventory: verify there is no hard-delete inventory action; use **Adjust stock** and **Edit thresholds** for corrections instead.
- Orders: `/orders` → NEW or CANCELLED row → **Archive order** → confirm; shipped/completed orders should show archive unavailable or a safe workflow error.
- Shipments: `/shipments` → row/card → **Archive shipment** → confirm; Nova Poshta TTNs are not cancelled by this action.
- Advertising campaigns: `/advertising` → campaigns table → **Archive campaign** → confirm and verify summaries refresh.
- Advertising metrics: `/advertising` → daily metrics table → **Delete metric** → confirm and verify summaries/trends refresh.
- RBAC: verify ANALYST users do not see destructive actions, and backend permission errors are friendly if a role is not allowed.
- Confirm archived/deleted records disappear from active lists and no sensitive records are hard deleted.

## Multi-Item Order QA

- Open `/orders`, click **Create order**, select one product variant, and verify **Unit price** auto-fills from the variant price.
- Change quantity and verify the item **Line total** and **Items subtotal** update immediately.
- Click **Add item**, select a different variant, and verify the second row also auto-fills price and updates totals.
- Remove an item row and confirm at least one item remains before submit.
- Submit a one-item order and verify the order row/detail revenue equals quantity × unit price.
- Submit a multi-item order and verify revenue equals the sum of all line totals.
- Open the order details panel and confirm every item is listed with quantity, product name, SKU, unit price, and line total.
- Verify inventory reserved quantities increase for every selected variant and the dashboard/order counters refresh.
- Confirm order status actions, safe-field order editing, and NEW/CANCELLED order archiving still work after multi-item order creation.
- Check the create-order dialog at mobile width: item rows should stack vertically, totals should remain readable, and there should be no horizontal overflow.

## Workspace Currency Settings QA

- Open `/settings` as an OWNER and verify the **Workspace settings** section is visible.
- Confirm the default currency is **UAH — Ukrainian hryvnia** for existing workspaces.
- Save currency as UAH and verify order, dashboard, analytics, and advertising monetary values display with `₴`.
- Change currency to USD and verify the same numeric values display with `$` without conversion.
- Confirm MANAGER and ANALYST accounts see the currency section as owner-only and cannot save workspace currency.

## Full Order Editing QA

- Create a one-item order from `/orders`, open row **Edit order**, and confirm the existing item is pre-filled.
- Add a second item, save, and verify order revenue/profit totals and inventory reserved quantity update for the added variant.
- Re-open **Edit order**, increase item quantity, save, and verify only the reservation delta is added.
- Re-open **Edit order**, decrease item quantity or remove an item, save, and verify released reservation quantity returns to available inventory.
- Replace an item variant, save, and verify the old variant reservation is released while the new variant is reserved.
- Try to edit items after changing an order to SHIPPED; item controls should be locked with a clear workflow message.
- Confirm safe fields such as payment status, costs, and notes still save for restricted statuses when allowed by backend policy.
- Confirm order details list every item with quantity, product name, SKU, unit price, line total, and workspace currency totals.

## Sprint 2.2 historical imports QA

- Confirm the Import Center preset selector includes `your_jewelry_orders_history_v1` and `your_jewelry_advertising_history_v1`.
- For historical orders, upload a small synthetic file, preview it, suggest mappings, and verify dry-run groups repeated order numbers into one multi-item order.
- Verify historical order dry-run counters for orders, order items, customers, variants, shipments, duplicate orders, estimated revenue, ad cost, and profit.
- Execute a synthetic historical orders import with `affect_inventory=false` and verify imported orders appear in `/orders` without changing current inventory reservations.
- Verify a row with a tracking number creates a Sellora shipment record only and does not call Nova Poshta.
- For advertising history, upload a small synthetic file, preview it, suggest mappings, and verify dry-run counters for campaigns, metrics, spend, revenue, net profit, and ROAS.
- Execute a synthetic advertising import and verify imported campaigns and daily metrics appear in `/advertising` and update dashboard/analytics summaries.
- Confirm duplicate orders and duplicate campaign/date metrics are skipped or warned in create-only mode.
- Confirm Import Logs for historical order and advertising imports do not store raw row values or private customer/order/ad data.
- Confirm product catalog import, create/edit/delete flows, auth/session refresh, workspace headers, and workspace currency formatting still work after historical imports.


## Localization QA

- Confirm first visit defaults to Ukrainian (`uk`).
- Switch to English from the topbar language switcher and confirm the app updates immediately.
- Switch language from Settings and confirm the preference persists after reload via `sellora_locale`.
- Verify enum labels are localized in the UI while submitted/backend values remain unchanged (`NEW`, `DELIVERED`, `PAID`, `ACTIVE`, etc.).
- Confirm create/edit/archive/import/order flows still submit backend enum values, not translated labels.
- Confirm the mobile language switcher is visible and does not cause topbar or drawer overflow.
- Scan main screens for mixed hardcoded Ukrainian/English labels before Sprint 2.3.

## Sprint 2.2.12 — Catalog Categories & Inventory UX QA

- Products category filtering
  - Confirm `/products` shows localized category chips for all products and common catalog categories.
  - Confirm selecting a category filters the product list and product cards/table show each product category.
  - Confirm search works together with the selected category.
  - Confirm create/edit product supports category while product archive/edit and variant management still work.
- Order item selection
  - Confirm Create/Edit Order uses category, product search/select, then variant/SKU selection instead of one unstructured large variant list.
  - Confirm changing category clears incompatible product/variant selections.
  - Confirm changing product scopes the variant list to that product.
  - Confirm variant labels include product name, SKU, color/size when present, available stock, and formatted price.
  - Confirm multi-item order creation, full order editing, inventory reservation, and price auto-fill still work.
- Inventory visual usability
  - Confirm `/inventory` shows product image or placeholder, category, product name, variant SKU, color/size, stock, reserved, incoming, minimum, status, and actions.
  - Confirm category filter and low-stock-only filter can be combined safely.
  - Confirm inventory transaction history, stock adjustment, and threshold editing still work.
  - Confirm mobile inventory cards are readable and do not cause body-level horizontal scrolling.
- Localization safety
  - Confirm new category/product/order/inventory UI appears in Ukrainian by default and in English after switching language.
  - Confirm category labels are localized at display level only; backend/API enum values and payload values remain stable.
  - Confirm no private catalog, customer, order, inventory, advertising, token, key, or workspace data appears in UI examples or docs.

## Sprint 2.2.13 — Pagination, List Performance & UX Cleanup QA

- Product pagination
  - Confirm `/products` renders 5 products by default and supports 15/30 page sizes.
  - Confirm page navigation works with category chips and product search.
  - Confirm changing search/category resets to page 1 while preserving page size.
  - Confirm mobile product cards and desktop table still show image/category/SKU/status/actions.
- Product variants pagination
  - Confirm Manage variants renders 5 variants by default and supports 15/30 page sizes.
  - Confirm create/edit/archive variant invalidates data and leaves pagination on a valid page.
  - Confirm variant SKU, product relationship, price, and actions remain visible.
- Inventory pagination
  - Confirm `/inventory` renders 5 rows/cards by default and supports 15/30 page sizes.
  - Confirm pagination works with category filter and low-stock-only filter.
  - Confirm product image/category/name/variant SKU remain visible in desktop table and mobile cards.
  - Confirm stock adjustment, transaction history, and threshold editing still work.
- Order product selector with images
  - Confirm Create/Edit Order product selection shows thumbnail or placeholder, name, SKU, category, available stock, and price.
  - Confirm product matches are limited by category/search before rendering options.
  - Confirm selected product scopes variants, clears invalid variant selections, and preserves price auto-fill.
- Shipments localization and scrollbar
  - Confirm `/shipments` header, KPI labels, status filter, search placeholder, empty detail prompt, table/cards, details, and form labels are localized in Ukrainian.
  - Confirm shipment status action labels are localized while backend status values remain unchanged.
  - Confirm shipment table uses Sellora scrollbar styling and mobile cards avoid body-level horizontal scroll.
- Large-list review decisions
  - Products, variants, and inventory received MVP frontend pagination because they are the largest catalog/inventory surfaces.
  - Orders, customers, leads, shipments, and advertising remain candidates for later server-backed pagination; this sprint only localized/polished shipments to avoid broad business-flow churn before Sprint 2.3.
- Full Ukrainian localization review
  - Review dashboard, products, orders, inventory, shipments, leads, customers, advertising, finance, reports, analytics, settings, topbar, sidebar, modals, dropdowns, empty/loading/error states, and buttons for obvious English UI.
  - Confirm technical IDs, route paths, provider constants, and backend/API enum values remain untranslated.


## Sprint 2.2.14 — Post-Pagination QA Fixes

### Orders product selector full catalog behavior
- Open `/orders`, create or edit an order, choose all categories, and confirm product search can find catalog items beyond the first visible selector subset.
- Choose a specific category and confirm search still checks the full category list before rendering compact visible options.
- Confirm product selector options show a compact thumbnail or placeholder, product name, SKU, category, stock and price metadata.

### Filters, sorting and global period selector
- Verify orders, products and inventory search/filter/sort controls reset cleanly and do not break existing create/edit/archive flows.
- Verify the topbar period selector supports Today, Last 7 days, Last 30 days, This month, All time and Custom period with date_from/date_to controls.
- Confirm date inputs keep ISO submission values while showing localized labels/helpers.

### Loading, empty/error states and scrollbars
- Confirm data-driven tables and selectors show loading states before empty states.
- Confirm table, modal, dropdown, product selector and transaction-history scroll areas use the Sellora scrollbar style and avoid body-level horizontal overflow.

### Inventory transaction history
- Confirm Transaction History shows five records by default, supports 5/15/30 page sizes and paginates independently from main inventory rows.
- Confirm transaction type, reason, quantity, stock and reserved labels are localized in Ukrainian while backend enum values remain unchanged.

### Integrations and Nova Poshta QA
- Confirm `/settings/integrations` is localized in Ukrainian, including connection, credential, sender settings and action labels.
- Search/select sender city, verify city ref populates, then search/select warehouse and verify warehouse ref populates.
- Confirm warehouse search stays disabled until a sender city ref is present and safe localized errors appear for API failures.
- Confirm ERROR badge and sender warning/info blocks are readable in dark theme.

### Full Ukrainian localization sweep
- Review `/dashboard`, `/orders`, `/products`, `/inventory`, `/settings/integrations`, `/shipments`, `/leads`, `/customers`, `/advertising`, topbar, sidebar, modals, badges, empty states and table headers for obvious English copy in Ukrainian mode.
- Confirm backend/API enum values and route/preset identifiers are not translated in submitted payloads.

## Sprint 2.3 — Analytics & Dashboard Polish on Real Data QA

### Dashboard date range integration
- Change the global/topbar period selector and the dashboard compact selector between Today, Last 7 days, Last 30 days, This month, All time, and Custom period.
- Confirm KPI cards, sales/profit chart, order funnel, top products, top categories, advertising summary, and recent orders refresh for the selected period.
- Confirm Custom period submits ISO-compatible `date_from`/`date_to` values while the UI remains localized.

### Real KPI cards and period comparison
- Confirm Revenue follows the existing analytics service totals for the selected period, while status-specific blocks clearly show cancelled/returned counts separately.
- Confirm Net Profit uses backend profit analytics only for roles allowed to see financial data; restricted roles see the localized hidden state.
- Confirm Orders and New Leads counts use records created in the selected period.
- Confirm ROAS uses advertising revenue/spend and shows `—` for zero spend instead of NaN or Infinity.
- Confirm previous-period deltas are calculated from the equivalent previous range or omitted when comparison data is unavailable; no static fake percentages should appear.

### Sales/profit chart and order status funnel
- Confirm the sales chart displays revenue and net profit over time for the selected period, with loading and empty states.
- Confirm order status funnel uses real counts for NEW, CONFIRMED, SHIPPED, DELIVERED, COMPLETED, RETURNED, and CANCELLED statuses.
- Confirm status labels are localized in Ukrainian/English while API enum values remain unchanged.
- Confirm charts remain readable in dark/light themes and do not overflow on mobile.

### Top products and top categories
- Confirm Top Products uses real order-item analytics and shows product name, SKU, category, quantity sold, revenue, optional profit, and thumbnail/placeholder.
- Confirm Top Categories groups sold items by localized product category, shows quantity, revenue, and revenue share, and falls back to Other/Інше when category data is missing.
- Confirm profit values are hidden for roles that should not see financial metrics.

### Advertising, inventory, and logistics summaries
- Confirm Advertising shows spend, revenue, ROAS, messages, orders, CPA, and CPL for the selected period with safe zero-denominator handling.
- Confirm Inventory Alerts show low-stock count, out-of-stock count, total stock units, and top low-stock items, or the healthy-state message when no alert exists.
- Confirm Logistics counters show in-transit, arrived, delivered-today, and returned-this-month counts from shipment data; note that active-state counters are intentionally current-state metrics.

### Recent orders, notifications, and activity
- Confirm Recent Orders shows order number, payment status, localized order status, revenue, optional profit, and created date without mobile overflow.
- Confirm dashboard notifications are actionable counts for low stock, out of stock, unpaid orders, and returned shipments, and show a healthy empty state when there is nothing urgent.
- Confirm the activity feed uses real recent orders/leads only and does not invent fake events.

### Localization, RBAC, and safety
- Review dashboard and analytics copy in Ukrainian and English, including metric tooltips/explanations, empty states, loading states, and errors.
- Confirm backend/API enum values are not translated in payloads or database values.
- Confirm auth/session/workspace headers still gate all dashboard queries and no cross-workspace data is visible.
- Confirm no secrets, tokens, workspace IDs, customer/order/profit details, Nova Poshta credentials, or private business data appear in docs, logs, source comments, or screenshots.

## Sprint 2.4 — Analytics Accuracy, Reports & Business Insights QA

### Formula source of truth
- Confirm `docs/analytics-metrics.md` defines revenue, net profit, AOV, margin, ROAS, CPA, CPL, conversion, return rate, repeat customer rate, low stock, and out-of-stock formulas.
- Confirm Dashboard and `/analytics` use the shared analytics formula helpers so revenue, ROAS, low stock, and zero-denominator behavior match for the same period.
- Confirm revenue includes NEW, CONFIRMED, SHIPPED, DELIVERED, and COMPLETED orders while excluding CANCELLED and RETURNED from revenue totals.

### Sales report
- Open `/analytics`, change the shared report period, and verify the Sales report updates.
- Confirm Sales report shows revenue, net profit when allowed, orders count, AOV, margin, return rate, cancelled orders, delivered orders, daily rows, order status breakdown, and payment status breakdown.
- Confirm AOV, margin, and return rate show `—` when denominators are zero.

### Product/category and inventory reports
- Confirm Product & Category report shows product, SKU, category, quantity sold, revenue, optional profit, current stock, reserved quantity, and status.
- Confirm Top Categories uses localized category labels and revenue share for the selected period.
- Confirm Inventory report shows low-stock count, out-of-stock count, reserved quantity, incoming quantity, and sales context for low-stock items.

### Advertising and customer reports
- Confirm Advertising report shows spend, revenue, ROAS, CPA, CPL, messages/leads/orders where available, and campaign rows.
- Confirm ROAS/CPA/CPL show `—` when spend/orders/leads denominators are zero and never show unsafe numeric values.
- Confirm Customer report shows new customers, repeat customer rate, average spend, customers with orders, top/recent customer rows, safe contact display, and last order date.

### Business insights and RBAC
- Confirm Business Insights are deterministic and based on real data: low stock, ad spend without orders, ROAS below 1, returns/cancellations, leads without orders, or healthy state.
- Confirm insights include type, title, description, source metric, and CTA where useful.
- Confirm unauthorized roles do not see restricted profit, margin, product cost, or profit trend values.

### Localization and safety
- Confirm Ukrainian and English analytics report labels, tooltips, empty states, errors, insight text, and table headers are localized.
- Confirm backend/API enum values remain unchanged and are only localized for display.
- Confirm no secrets, tokens, workspace IDs, API keys, customer private data, order data, profit data, or advertising data appear in docs, logs, examples, screenshots, or comments.

## Sprint 2.5 — Analytics Backend Hardening QA

- [ ] `/api/v1/analytics/sales-report` returns period-aware revenue, AOV, status breakdowns, and null restricted profit fields for non-authorized roles.
- [ ] `/api/v1/analytics/products-report` uses captured order-item totals, not current product prices, and respects workspace isolation.
- [ ] `/api/v1/analytics/advertising-report` returns null for ROAS/CPA/CPL/CTR/CPM when denominators are zero.
- [ ] `/api/v1/analytics/customers-report` and `/api/v1/analytics/inventory-report` exclude soft-deleted records.
- [ ] `/api/v1/analytics/business-insights` returns deterministic localization keys and no invented private data.
- [ ] `/api/v1/analytics/dashboard-summary` keeps Dashboard KPI values consistent with Reports for the same date range.
- [ ] Frontend `/dashboard` and `/analytics` use backend aggregates where available and show loading, empty, error, and restricted states safely.
- [ ] `npm --prefix frontend run typecheck` and backend analytics tests pass or any unrelated existing issues are documented.

## Sprint 2.6 — Import and Demo Dataset QA

- [ ] Product catalog dry-run reports expected columns, missing required fields, row-level warnings/errors, duplicate products/variants, and inventory row counts.
- [ ] Product catalog import matches by product SKU or normalized product name and by variant SKU or product/color/size fallback.
- [ ] Catalog import initializes `stock_quantity`, `incoming_quantity`, and `minimum_quantity` without changing `reserved_quantity`.
- [ ] Historical order dry-run groups repeated order numbers into multi-item orders and reports duplicate order warnings.
- [ ] Historical order import matches customers by normalized phone/Instagram and keeps `affect_inventory=false` by default.
- [ ] Advertising history dry-run reports duplicate campaign/date metrics and safe estimates for spend/revenue/ROAS.
- [ ] `backend/scripts_seed_demo.py` creates only synthetic DEMO records and can be run twice without duplicates.
- [ ] After demo seed/import, Dashboard and Analytics reports show non-empty revenue, top products, advertising metrics, customer totals, inventory alerts, and business insights.

## Sprint 2.7 — Demo Workspace, Onboarding and Pilot Readiness QA

- [ ] Demo seed runs once and can be rerun without duplicating DEMO records.
- [ ] Demo badge/notice appears only for demo workspace and never exposes workspace IDs.
- [ ] Dashboard setup checklist appears, is localized, and links to Products, Import, Orders, Advertising, Integrations and Analytics.
- [ ] Empty/new workspace shows useful first-run CTAs without appearing during loading.
- [ ] Import Center helper text explains dry-run, warnings, errors, duplicates and next actions after a successful dry-run.
- [ ] Pilot docs exist: `pilot-onboarding-guide.md`, `demo-script.md`, `pilot-qa-checklist.md`, and `mvp-readiness.md`.
- [ ] Mobile QA covers Dashboard, Orders, Products, Inventory, Analytics, Import Center, Integrations and Advertising at 375px, 390px, 430px and 768px.
- [ ] Demo workspace Dashboard and Analytics show meaningful data after `backend/scripts_seed_demo.py`.
- [ ] Safety/privacy scan confirms no real private data, tokens, workspace IDs, API keys or private spreadsheets were committed.

## Sprint 2.8 — Pilot Feedback and Pre-MVP Release QA

- [ ] Feedback button is visible in the topbar and opens a mobile-safe modal.
- [ ] Feedback form requires category and message, supports optional rating, captures current page path, and shows privacy hint.
- [ ] Feedback submit button has loading state, success state and error state.
- [ ] `/settings/feedback` is workspace-scoped and available only to roles allowed by backend RBAC.
- [ ] Owner can update feedback status; restricted users cannot manage feedback.
- [ ] Pre-MVP checklist, known limitations, pilot release notes and feedback process docs exist and are honest about MVP limitations.
- [ ] Empty/loading/error final pass confirms empty states do not appear during loading and submit buttons disable while submitting.
- [ ] Mobile QA includes feedback modal/form at 375px plus Dashboard, Analytics, Orders, Products, Inventory, Import Center and Advertising.
- [ ] Safety scans show no secrets, API keys, tokens, workspace IDs, private spreadsheets or real private customer/order data.

## Sprint 2.9 — Mobile UX, Feedback Modal & Orders List Polish

### Mobile sidebar footer
- [ ] At 375px, the sidebar footer profile row is compact and the user email truncates with ellipsis.
  Expected result: language switcher and theme toggle align in one compact row; logout is a compact full-width secondary action.
  Notes:
  Severity if failed: Major

### Mobile topbar
- [ ] At 375px / 390px / 430px, topbar stays on one row with menu, logo, primary create action and More menu.
  Expected result: feedback, language and theme are accessible from More without wrapping the topbar.
  Notes:
  Severity if failed: Major

### Custom period and calendar icon visibility
- [ ] Dashboard custom period date inputs stack without viewport overflow.
  Expected result: date_from/date_to fields are fully visible and native calendar icons have contrast in light and dark themes.
  Notes:
  Severity if failed: Major

### Feedback modal
- [ ] Feedback opens as a centered modal on desktop and a full-width bottom sheet on mobile.
  Expected result: overlay appears, the modal is not clipped, fields are fillable, and submit/cancel remain visible.
  Notes:
  Severity if failed: Major

### Reports navigation
- [ ] Sidebar “Звіти” route opens the active Analytics reports experience.
  Expected result: /reports survives reload via the alias and existing /analytics links still work.
  Notes:
  Severity if failed: Major

### Orders pagination
- [ ] /orders shows 5 orders by default with page size options 5 / 15 / 30.
  Expected result: pagination works with search, order status, payment status and sorting; filter changes reset to page 1.
  Notes:
  Severity if failed: Major

### Responsive breakpoints
- [ ] Verify /dashboard, /orders, /products, /inventory, /analytics, /settings, feedback modal and sidebar drawer at 375px / 390px / 430px / 768px.
  Expected result: no body-level horizontal overflow and dark/light contrast remains acceptable.
  Notes:
  Severity if failed: Major

### Sprint 2.9 follow-up — Responsive feedback and analytics cleanup
- [ ] Feedback modal positioning is re-tested on desktop and mobile.
  Expected result: modal is rendered above topbar/sidebar with overlay, centered desktop behavior, bottom-sheet mobile behavior, internal scroll, and visible close/submit/cancel controls.
  Notes:
  Severity if failed: Major

- [ ] Mobile More menu is re-tested at 375px / 390px / 430px.
  Expected result: menu is viewport-safe, not clipped by topbar overflow, readable in dark/light themes, and closes on outside click or action.
  Notes:
  Severity if failed: Major

- [ ] Analytics detailed sales table pagination is re-tested.
  Expected result: /analytics defaults to 5 rows, supports 5 / 15 / 30, resets page to 1 when the period changes, and does not show a false empty state during loading.
  Notes:
  Severity if failed: Major

- [ ] Shared topbar global period selector is removed while local selectors remain.
  Expected result: Dashboard and Analytics local period selectors still work; shared header is less overloaded and buttons align consistently.
  Notes:
  Severity if failed: Major

## Sprint 3.0 — Nova Poshta production validation QA

### Settings and credential safety
- [ ] Save the Nova Poshta credential through Settings → Integrations only.
  Expected result: saved state is masked; raw credential is not shown after save and not present in visible logs.
  Notes:
  Severity if failed: Critical

- [ ] Test Nova Poshta connection from Settings → Integrations.
  Expected result: success or failure is localized and safe; no raw third-party payload is shown.
  Notes:
  Severity if failed: Major

### Sender settings and directories
- [ ] Search sender city and select a result.
  Expected result: sender city ref is filled and stale warehouse ref is cleared if city changes.
  Notes:
  Severity if failed: Major

- [ ] Search sender warehouse after city selection.
  Expected result: warehouse search is disabled before city selection and shows loading, empty, and safe error states.
  Notes:
  Severity if failed: Major

### Shipment and order flow
- [ ] Create shipment from an order.
  Expected result: the shipment form opens with the order selected, requires recipient and delivery data, and links the shipment back to the order.
  Notes:
  Severity if failed: Major

- [ ] Create a Nova Poshta TTN for a prepared shipment.
  Expected result: tracking/TTN is saved on the shipment, visible on order details, and duplicate TTN creation is blocked or warned.
  Notes:
  Severity if failed: Critical

- [ ] Sync Nova Poshta status when supported.
  Expected result: status updates safely or shows a localized unavailable message without completing the order automatically.
  Notes:
  Severity if failed: Major

## Sprint 3.1 — Shipment UX, TTN documents and delivery status QA

- [ ] `/shipments` list shows TTN/order/customer/carrier/status/destination/updated context.
- [ ] Search covers TTN, order number, customer name/phone, city and warehouse.
- [ ] Carrier, status, TTN state and needs-action filters reset pagination to page 1.
- [ ] Shipment detail shows grouped Order, Customer, Recipient, Nova Poshta, TTN and Status sections.
- [ ] Copy TTN works on desktop and mobile, or shows a safe clipboard error.
- [ ] Create TTN is disabled when a TTN already exists and duplicate attempts show localized messaging.
- [ ] Sync status is disabled until TTN exists and shows safe unavailable messaging if Nova Poshta cannot be reached.
- [ ] TTN print/download is documented as unavailable; no fake document is shown.
- [ ] Creating a TTN does not automatically complete the order.
- [ ] OWNER/MANAGER mutation actions and ANALYST read-only expectations remain enforced by backend RBAC.

## Sprint 3.2 — Nova Poshta staging edge cases

- [ ] Complete `docs/nova-poshta-staging-validation.md` using a controlled staging account and synthetic customer/order data.
- [ ] Validate no-key, invalid-key, revoked-key and missing-sender-settings states with localized safe messages.
- [ ] Confirm sender warehouse is disabled before city selection and clears when sender city changes.
- [ ] Confirm recipient phone/city/warehouse missing states are user-friendly before TTN creation.
- [ ] Confirm incomplete TTN responses do not save tracking data.
- [ ] Confirm status sync without TTN is blocked and unavailable status sync does not show raw payloads.
- [ ] Confirm OWNER/MANAGER/ANALYST expectations and cross-workspace access blocking.
- [ ] Confirm audit/logs contain no raw API key or raw Nova Poshta payload.
- [ ] Confirm `/settings/integrations`, `/orders`, `/shipments`, shipment modal and shipment detail are usable at 375px.

## Sprint 3.2.1 — Environment and CI recovery

- [x] Backend dependency environment diagnosed: previous failures were caused by missing local dependencies plus external registry/proxy install failures, not by Nova Poshta code.
- [x] Backend `compileall`, full `pytest`, and app import checks pass in the recovered environment.
- [x] Frontend typecheck and production build pass in the recovered environment.
- [ ] Frontend lint remains an interactive Next.js ESLint setup prompt until ESLint config is added/migrated.
- [x] Full regression script suite passes, including Sprint 3.x Nova Poshta checks.
- [ ] Real Nova Poshta staging validation remains blocked until a controlled real API key is provided.

## Sprint 4.0 — Advertising integration foundation

- [ ] `/advertising` loads and explains that manual/imported metrics are the active MVP source.
- [ ] Campaign list shows campaign name, platform, data source, status, budgets and actions without exposing technical token fields.
- [ ] Imported/manual spend, leads, messages, orders and revenue feed advertising summaries consistently.
- [ ] ROAS, CPA, CPL, ROI, conversion rate and cost-per-message cases with zero denominators show `—`, not `NaN` or `Infinity`.
- [ ] `/settings/integrations` shows Meta Ads as a preparation/placeholder state and does not imply automatic sync is active.
- [ ] OWNER-only credential-management expectation is documented; no raw Meta token, app secret, ad account ID or business ID appears in UI/logs/docs.
- [ ] Cross-workspace advertising campaigns, metrics and future integration settings remain isolated by `workspace_id`.

## Sprint 4.0.1 — Advertising foundation validation recovery

- [x] Backend environment recovered: dependencies are available locally and `compileall`, full `pytest`, and FastAPI app import pass.
- [x] Frontend validation recovered: TypeScript typecheck and production build pass with local `frontend/node_modules`.
- [ ] Frontend lint remains an interactive/deprecated `next lint` setup prompt until ESLint CLI config is migrated.
- [x] Sprint 4.0 advertising regression script and the full relevant frontend regression suite pass.
- [ ] Manual staging browser QA for `/advertising`, `/settings/integrations`, Dashboard, Analytics and Import Center remains pending until staging URL/credentials are provided.
- [ ] Manual synthetic advertising import verification remains pending until staging access is available; use only synthetic campaign data.
