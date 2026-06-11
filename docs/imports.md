# Sellora Imports — Sprint 2.6 Stabilization

Sellora imports are workspace-scoped, RBAC-protected, dry-run first, and designed for synthetic/demo or owner-provided spreadsheet migration data. Do not commit real shop spreadsheets or copied private rows.

## Supported import types

| Import type | Preset | Main entities | Duplicate key | Default behavior |
| --- | --- | --- | --- | --- |
| Product catalog | `your_jewelry_product_catalog_v1` | Products, variants, inventory, product images | Variant SKU; fallback product + color + size | Skip existing variant and warn. Product can match by product SKU or normalized product name if SKU is missing. |
| Historical orders | `your_jewelry_orders_history_v1` | Customers, orders, order items, optional shipments | Order number | Skip existing order and warn. Repeated order number rows are grouped into one multi-item order. |
| Advertising history | `your_jewelry_advertising_history_v1` | Campaigns and daily ad metrics | Campaign + metric date | Reuse campaign by workspace + name + platform; skip duplicate daily metric and warn. |

## Product catalog columns

Required: product name or product SKU; variant SKU or color/size fallback; price; quantity. Optional: category, brand, barcode, cost, minimum quantity, incoming quantity, image URL/gallery, status/visibility, currency.

Matching rules:

1. Product match: `workspace_id + product SKU`.
2. Fallback product match: normalized product name when product SKU is missing.
3. Variant match: `workspace_id + variant SKU`.
4. Fallback variant match: `product_id + color + size`.

Inventory behavior: catalog import initializes or updates current `stock_quantity`, `incoming_quantity`, and `minimum_quantity`. It does not set `reserved_quantity` and does not create historical stock transactions in Sprint 2.6.

## Historical orders columns

Supported fields include order number/date, customer name, phone, Instagram username, variant SKU, product name, quantity, unit price, unit cost, shipping cost, ad cost, COD fee, other cost, payment status, order status, tracking number, carrier, city, warehouse, and notes.

Historical order behavior:

- Rows with the same order number are grouped into one order with multiple items.
- Customers are matched by normalized phone first, then normalized Instagram username, then exact name as a weak fallback.
- Product variants must match by SKU before final import.
- Captured order item prices and costs are preserved on order items.
- Imported orders are marked historical.
- `affect_inventory=false` by default, so historical orders do not reserve or deduct current stock unless explicitly enabled.

## Advertising history columns

Supported fields include date, campaign name, platform, spend, impressions, reach, clicks, messages, leads, orders, revenue, net profit, and notes.

Advertising import behavior:

- Campaigns match by workspace + campaign name + platform.
- Missing campaigns are created for supported historical imports.
- Duplicate campaign/date metrics are skipped with warnings.
- ROAS/CPA/CPL are calculated by analytics reports after import and zero denominators render as unavailable in the frontend.

## Dry-run and result reporting

Dry-run returns a structured report with total rows, valid/invalid rows, created/updated estimates, skipped rows, warnings/errors counts, duplicate counters, row-level `errors_by_row`, row-level `warnings_by_row`, and sample warnings/errors. Dry-run does not mutate business records.

## Migration safety

No schema migration is required for Sprint 2.6. Existing migrations remain additive. Import queries and writes must remain scoped to `workspace_id`, and soft-deleted records are ignored for duplicate checks unless intentionally restored by a future feature.
