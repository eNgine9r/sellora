# Sprint 8C — Import Center Staging Closure

## Final decision

**APPROVED — CONTROLLED GUIDED PILOT ✅**

Sprint 8C Import Center staging closure passed against the identified Render runtime commit:

`39c46dcf339990e491c9dfa25f1b75fad7c9289a`

This approval applies to the controlled pilot scope and synthetic QA workspace. It does not expand Import Center beyond the documented pilot contracts or enable live Meta Ads / Nova Poshta calls.

## Runtime and durability evidence

- Backend `/health` returned `200` with the expected runtime commit and process-start marker.
- A successful PostgreSQL-backed dry-run approval survived a real Render process boundary.
- Execute revalidated workspace, job, source bytes, entity type, sheet, mapping, and options.
- Changed mapping/options/source were rejected.
- Source files used private Supabase Storage URIs with workspace/job-bound object keys.
- Cross-workspace source, job, log, and business-data access were denied.

## Phase B core result

GitHub Actions run `29401564796` completed successfully.

- 213 checks passed; 0 failed.
- OWNER/MANAGER/ANALYST runtime behavior passed.
- Customers, products, product variants, inventory, order history, and advertising history passed.
- Shipments remained explicitly unsupported in the controlled pilot.
- Duplicate behavior, malformed files, invalid values, formula-prefixed input, missing mapping, and row-level errors passed.
- Atomic rollback and historical side-effect safety passed.
- Import logs contained no raw source rows.
- No Meta Ads or Nova Poshta calls were introduced.

## Performance and browser result

GitHub Actions run `29403006290` completed successfully.

- 153 checks passed; 0 failed.
- 100-row dry-run total: 6.302 seconds.
- 1,000-row dry-run total: 29.114 seconds.
- 5,000-row dry-run total: 122.701 seconds.
- 5,001 rows were rejected safely with the documented 5,000-row limit.
- 10 screenshots covered 1366×768, 375×812, 390×844, 430×932, and 768×1024 in light and dark themes.
- 528 browser network events were reviewed.
- Browser page errors: 0.
- Unexpected console errors: 0.
- Request failures: 0.
- HTTP 5xx responses: 0.
- Meta Ads / Nova Poshta browser requests: 0.
- MANAGER and ANALYST browser uploads returned the expected backend `403` denial.
- Execute was disabled before dry-run, enabled only after a matching dry-run, protected by confirmation, and invalidated after mapping or workspace changes.

## Cleanup and evidence retention

- Active `QA8C*` customers, products, variants, orders, campaigns, metrics, and related records were soft-deleted from the dedicated QA workspace after closure.
- No historical shipment remained from the imported order scenarios.
- Final performance/browser runs used dry-run only and created no business entities.
- Import jobs, audit events, and private Supabase source objects remain as controlled staging evidence and are subject to the configured evidence/storage lifecycle.
- QA runner PR #159 was intentionally not merged into `main`.

## Approved pilot boundaries

- Supported files: `.csv` and `.xlsx`.
- Effective limits: 10 MB, 5,000 data rows, 100 columns, and 20 sheets.
- OWNER-only upload, validation, dry-run, and execute.
- Safe duplicate policy: skip, warning, or reject according to the documented entity contract.
- Dry-run is mandatory before execute.
- Historical order import does not automatically create shipments and does not affect current inventory unless the explicit supported option is selected.
- Raw source rows must not be persisted in import logs or QA artifacts.

## Remaining product boundaries

- This is controlled-pilot approval, not unrestricted production approval.
- Shipments import remains unavailable in the controlled pilot.
- Live Meta Ads synchronization is not active.
- Nova Poshta external calls are outside Import Center closure scope.
- Private import-source lifecycle automation may be expanded in later operational hardening work.
