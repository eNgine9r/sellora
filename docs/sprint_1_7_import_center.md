# Sprint 1.7 Import Center

Sprint 1.7 adds an owner-only Excel Import Center for historical Sellora data.

## Workflow

1. Upload `.xlsx` files to local storage under `storage/imports/{workspace_id}/{job_id}`.
2. List workbook sheets.
3. Preview selected sheet rows without writing business data.
4. Validate column mappings for customers, products, product variants, inventory, or orders.
5. Execute `create_only` imports with row-level `ImportJobLog` records.
6. Review logs and summary counters.

## Security

- Import endpoints require `OWNER` role.
- File extension and file size are validated.
- Local file paths are not returned to the frontend.
- Excel formulas are treated as data by reading workbooks with `data_only=True`.
- Google Sheets, Meta Ads, Nova Poshta, and AI Insights remain out of scope.

## Preset

`your_jewelry_excel_v1` includes suggested mappings for the expected jewelry workbook sheets, but users still preview and confirm mappings before importing.
