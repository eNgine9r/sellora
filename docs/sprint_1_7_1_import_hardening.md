# Sprint 1.7.1 Import Hardening

Sprint 1.7.1 hardens the Import Center for confidential real-world Excel imports without committing private files or real row values.

## Confidentiality guardrails

- Real spreadsheets remain local and are ignored by Git.
- Tests use synthetic data only.
- Documentation includes expected sheet names and column aliases only, never real customer, order, product, cost, profit, advertising, or inventory values.
- Audit events for dry run and validation store aggregate counts instead of full row data.

## Added capabilities

- `POST /api/v1/import/{job_id}/dry-run` reads, maps, validates, detects duplicates, and returns an import report without writing business records.
- `POST /api/v1/import/{job_id}/suggest-mapping` suggests mappings from sheet columns and generic aliases.
- `GET /api/v1/import/presets/your-jewelry` returns the `your_jewelry_excel_v1` sheet/alias preset.
- `ExcelValueNormalizer` handles empty/dash cells, whitespace, evaluated formulas, currency-like strings, comma decimals, dates, Excel serial dates, percentages, and boolean-like strings.
- Validation returns row-level issues with severity, field, message, raw value, and normalized value to the authenticated owner only.

## Out of scope

Meta Ads API, Nova Poshta API, and AI Insights remain out of scope.
