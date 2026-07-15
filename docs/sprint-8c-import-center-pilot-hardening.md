# Sprint 8C — Import Center Pilot Hardening

## Final decision

**Sprint 8C — APPROVED FOR CONTROLLED GUIDED PILOT ✅**

The final staging evidence is documented in `docs/sprint-8c-staging-closure.md`.

## Existing capability inventory

Audited backend import routes, schemas, parser, mapping suggestion, validation, dry-run, execute, logs, RBAC, workspace filtering, historical order behavior, inventory option, advertising calculations, and frontend `/settings/import` wizard components.

| Import type | Template | Preview | Mapping | Dry-run | Execute | Duplicates | Logs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Customers | actual | actual | actual | actual | actual | workspace-local phone/Instagram | actual |
| Products | actual | actual | actual | actual | actual | workspace-local SKU | actual |
| Product variants | actual | actual | actual | actual | actual | workspace-local variant SKU | actual |
| Inventory | actual | actual | actual | actual | actual | absolute update/warning rules | actual |
| Product catalog | actual | actual | actual | actual | actual | product/variant duplicate warnings | actual |
| Orders history | actual | actual | actual | actual | actual | order number/historical duplicate checks | actual |
| Advertising history | actual | actual | actual | actual | actual | campaign/date checks | actual |
| Shipments | unavailable in controlled pilot | unavailable | unavailable | rejected | rejected | n/a | n/a |

## Supported file formats and limits

`.xlsx` and `.csv` only; effective pilot limit is 10 MB, 5,000 rows, 100 columns, and 20 sheets. Macro-enabled spreadsheets, invalid workbook content, binary CSV, unsupported encodings, duplicate headers, and excessive row/column counts are rejected.

## Template contracts

See `docs/import-template-contracts.md`. Your Jewelry presets remain alias/template contracts only and must not include real customer/order exports.

## Mapping behavior

Headers are normalized by trimming, collapsing spaces, and case-insensitive Ukrainian/English alias matching. Duplicate normalized headers are rejected to prevent ambiguous mapping.

## Validation model

See `docs/import-validation-error-catalog.md`. Errors block execute; warnings separate duplicates and non-destructive concerns. Formula-prefixed cells and invalid non-empty historical dates/statuses are rejected with structured row evidence.

## Duplicate policy

Default pilot behavior is safe skip/warning/reject. Existing records are not silently overwritten. Duplicate matching is workspace-local and blank identifiers are not keys.

## Dry-run and execute semantics

Dry-run parses the same file/sheet/mapping/options as execute, writes no business records, records a durable PostgreSQL-backed approval signature, and marks the job executable only after a successful report.

Execute requires a matching successful dry-run, revalidates rows before writes, and rejects unsupported modes. The signature binds workspace, job, source bytes, entity type, sheet, mapping, and options. The UI invalidates approval on workspace, file, sheet, import type, mapping, or option changes.

## Durable source storage

Import source files are stored in the private Supabase bucket `sellora-import-sources` with server-generated workspace/job-bound keys. `ImportJob.file_path` stores a `supabase://...` reference. Source bytes are materialized temporarily only for parser work.

A real Render process restart proved that the same approved job/input remained executable after the local filesystem boundary.

## Historical order semantics

Historical order import is not a live operational replay. It does not call external shipment providers and does not automatically create shipment records. Shipment-related source columns are ignored in the controlled pilot. Inventory impact remains explicit; default historical import does not affect current inventory.

## Inventory semantics

Inventory rows import physical stock fields only through supported inventory contracts. Negative quantities are rejected. Existing inventory is planned truthfully as an absolute update rather than a duplicate create.

## Rollback behavior

The controlled pilot policy is all-or-nothing. Blocking validation errors prevent writes, and the staging atomic rollback scenario confirmed that controlled execution failure leaves no partial business entities.

## RBAC and workspace isolation

OWNER can run the full Import Center flow. MANAGER and ANALYST are denied upload/execute by backend guards. Browser evidence confirmed both denials with expected `403` responses.

Jobs, sources, approvals, logs, matching, and business writes are scoped by `workspace_id`. Cross-workspace job/log/source access is denied, and switching workspace clears the frontend import state and execute approval.

## Runtime staging result

Phase B core run `29401564796` passed 213 checks with 0 failures against Render runtime commit `39c46dcf339990e491c9dfa25f1b75fad7c9289a`.

Coverage included supported import types, durable restart approval, source/mapping/options mutation denial, duplicates, malformed files, invalid values, formula rejection, atomic rollback, RBAC, workspace isolation, sanitized logs, and historical side-effect safety.

## Performance benchmark

Final closure run `29403006290` passed:

- 100 rows: 6.302 seconds total;
- 1,000 rows: 29.114 seconds total;
- 5,000 rows: 122.701 seconds total;
- 5,001 rows: safely rejected in 0.956 seconds.

These are staging measurements on the current free-tier environment, not a production SLA.

## Browser/mobile QA

Final closure passed 153 checks with 0 failures:

- 10 screenshots across 1366×768, 375×812, 390×844, 430×932, and 768×1024;
- light and dark themes;
- 528 network events reviewed;
- 0 unexpected console errors;
- 0 page errors;
- 0 request failures;
- 0 HTTP 5xx responses;
- 0 Meta Ads / Nova Poshta requests;
- execute disabled before dry-run, enabled only for matching approval, protected by confirmation, and invalidated after mapping/workspace changes.

## Privacy and cleanup

Import logs do not persist raw source rows. QA artifacts suppress passwords, tokens, authorization headers, API keys, and source rows.

After closure, active `QA8C*` business fixtures were soft-deleted from the dedicated QA workspace. Import jobs, audit records, and private source objects remain controlled staging evidence subject to the configured lifecycle.

## Remaining limitations

- Approval is for controlled guided pilot, not unrestricted public production.
- Shipments import remains unavailable in the controlled pilot.
- Live Meta Ads synchronization remains inactive.
- Nova Poshta external calls remain outside Import Center scope.
- Issue #134 archived variants and zero-stock rows remain a separate focused QA concern.
- Private source-object lifecycle automation may be expanded in later operational hardening.

## Pilot recommendation

Import Center may be enabled for the controlled guided pilot within the documented contracts, role restrictions, file limits, and monitoring expectations.
