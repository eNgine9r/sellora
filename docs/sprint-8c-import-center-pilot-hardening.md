# Sprint 8C — Import Center Pilot Hardening

## Existing capability inventory

Audited backend import routes, schemas, parser, mapping suggestion, validation, dry-run, execute, logs, RBAC, workspace filtering, historical order behavior, inventory option, advertising calculations, and frontend `/settings/import` wizard components.

| Import type | Template | Preview | Mapping | Dry-run | Execute | Duplicates | Logs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Customers | actual | actual | actual | actual | actual | workspace-local phone/Instagram | actual |
| Products | actual | actual | actual | actual | actual | workspace-local SKU | actual |
| Product variants | actual | actual | actual | actual | actual | workspace-local variant SKU | actual |
| Inventory | actual | actual | actual | actual | actual | duplicate SKU warnings | actual |
| Product catalog | actual | actual | actual | actual | actual | product/variant duplicate warnings | actual |
| Orders history | actual | actual | actual | actual | actual | order number/historical duplicate checks | actual |
| Advertising history | actual | actual | actual | actual | actual | campaign/date checks | actual |
| Shipments | mapping-based | actual | actual | actual | actual | order/tracking checks | actual |

## Supported file formats and limits

`.xlsx` and `.csv` only; effective pilot limit is 10 MB, 5,000 rows, 100 columns, and 20 sheets. Macro-enabled spreadsheets, invalid workbook content, binary CSV, unsupported encodings, duplicate headers, and excessive row/column counts are rejected.

## Template contracts

See `docs/import-template-contracts.md`. Your Jewelry presets remain alias/template contracts only and must not include real customer/order exports.

## Mapping behavior

Headers are normalized by trimming, collapsing spaces, and case-insensitive Ukrainian/English alias matching. Duplicate normalized headers are rejected to prevent ambiguous mapping.

## Validation model

See `docs/import-validation-error-catalog.md`. Errors block execute; warnings separate duplicates and non-destructive concerns.

## Duplicate policy

Default pilot behavior is safe skip/warning/reject. Existing records are not silently overwritten. Duplicate matching is workspace-local and blank identifiers are not keys.

## Dry-run semantics

Dry-run parses the same file/sheet/mapping/options as execute, writes no business records, records an audit-safe signature, and marks the job executable only after a successful report.

## Execute semantics

Execute requires successful dry-run, revalidates rows before writes, and rejects unsupported modes. The UI invalidates dry-run on workspace, file, sheet, import type, mapping, or option changes.

## Historical order semantics

Historical order import is not a live operational replay. It does not call external shipment providers. Inventory impact remains opt-in and visible; default historical import does not affect current inventory.

## Inventory semantics

Inventory rows import physical stock fields only through supported inventory contracts. Negative quantities are rejected. Reserved/available quantities must not be used as arbitrary user-controlled truth.

## Rollback behavior

The policy remains all-or-nothing for pilot execution. A blocking validation error prevents business writes. A deeper transactional rollback proof is covered locally by service tests and remains a required staging gate before full 8C approval.

## RBAC

OWNER can run the full Import Center flow. ANALYST direct execution is denied by backend owner-only guards. MANAGER remains denied for execution under the current safe pilot rule unless backend policy changes later.

## Workspace isolation

Jobs and logs are scoped by `workspace_id`; switching workspace clears import state in the UI. Cross-workspace matching is rejected by repository methods that always filter by active workspace.

## Performance benchmark

Local code enforces a 5,000 row limit. Staging benchmarks for 100 and 1,000 rows are pending because no staging import credentials/browser runner were available in this environment.

## Browser/mobile QA

Responsive import state clearing and dry-run gating were implemented in the React page. Manual browser/mobile staging QA for 1366, 375, 390, 430, and 768 widths remains pending until staging credentials are available.

## Staging import result

Not executed in this environment. This blocks claiming full Sprint 8C approval under the Sprint rules.

## Issues found and fixed

- Execute could be clicked after mapping/workspace changes; fixed by clearing import state and gating execute on matching dry-run state.
- Upload accepted only by extension; hardened with workbook magic, UTF-8/binary CSV checks, and effective 10 MB pilot limit.
- Parser accepted duplicate headers; hardened with duplicate normalized-header rejection.
- Dry-run did not mark successful jobs as the prerequisite for execute; fixed with a successful dry-run gate.

## Remaining limitations

- No new persistence column was added for a durable dry-run token because Sprint 8C prohibits migrations; audit signature is recorded, and execute revalidates before writes.
- Full staging import gates and browser/mobile proof remain pending.
- Issue #134 archived variants and zero-stock rows need continued focused QA.

## Sprint status

Sprint 8C — BLOCKED ⚠️ for final approval until real staging imports and browser/mobile QA are executed.

## Pilot recommendation

Controlled guided pilot remains GREEN. Import Center is locally hardened for controlled pilot QA, but import pilot execution should remain gated until staging import evidence is complete.
