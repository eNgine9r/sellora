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
