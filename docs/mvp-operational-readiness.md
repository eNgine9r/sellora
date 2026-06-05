# MVP Operational Readiness

This runbook describes how to prepare Sellora for real operations without committing private files or business data.

## Product catalog import

1. Open `/settings/import`.
2. Upload a local product catalog spreadsheet from your private machine.
3. Select the `your_jewelry_product_catalog_v1` preset.
4. Preview the sheet and confirm that product catalog columns are detected.
5. Run **Suggest mapping** and review the suggested product, variant, inventory, and image fields.
6. Run **Dry run** before any execution.
7. Review errors first, then warnings. Do not execute while error rows exist.
8. Execute only after the dry-run report looks correct.

The product catalog preset creates Products, Product Variants, Inventory, and Product Images in `create_only` mode. It does not overwrite existing records.

## Reading warnings and errors

- Errors block import for affected rows. Fix missing product SKU, missing variant SKU, missing product name, or invalid price before execution.
- Warnings should be reviewed but do not always block import. Typical warnings include missing image, missing category, unknown availability, defaulted visibility, non-UAH currency, or duplicate records.
- Availability may derive inventory when quantity is empty or zero.

## Import order

1. Import products and variants first.
2. Verify `/products` and product variant selectors.
3. Verify `/inventory` records.
4. Import or create orders only after products and variants exist.
5. Verify dashboard and analytics after orders and advertising data are present.

## Safe staging rollout

If you need a small test subset, create a private copy of the spreadsheet with only a few synthetic or approved rows and import that first. Do not commit the copied spreadsheet.

## Manual rollback guidance

If an import was incorrect, do not upload or expose private data in support channels. Use admin-only database tools to identify records created by the import job, then soft-delete or correct them according to the current operational policy. Re-run dry-run after corrections before another import.

## Privacy rules

- Do not commit real Excel, CSV, or exported business files.
- Do not paste real product names, prices, costs, customer details, order details, URLs, or profit data into docs, tests, screenshots, issue comments, or logs.
- Keep uploaded files in private import storage only.

## Historical import readiness

1. Import the synthetic-reviewed product catalog first so Products, Product Variants, and Inventory exist before historical sales are loaded.
2. Verify products, variants, prices, and inventory rows before importing order history.
3. Import historical orders second with `your_jewelry_orders_history_v1`.
4. Always run preview, suggested mapping, validation, and dry-run before execution.
5. Keep `affect_inventory` disabled for historical completed orders so current stock and reserved quantities are not changed.
6. Import advertising daily metrics third with `your_jewelry_advertising_history_v1`.
7. Verify dashboard, analytics, ROAS, and profit summaries after each import batch.
8. Use edit/archive flows to correct mistakes instead of overwriting historical imports.
9. Never commit real spreadsheets, raw order rows, customer private data, product costs, profit data, or ad performance data.
10. Prefer a small synthetic or anonymized test subset before a full private import.
