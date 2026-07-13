# Import Template Contracts — Sprint 8C

Sellora supports pilot imports only through explicit template contracts. Templates and presets are synthetic; source files are processed as workspace-scoped temporary uploads and must not contain real pilot data in Git.

## Supported pilot formats and limits

| Limit | Contract |
| --- | --- |
| Extensions | `.xlsx`, `.csv` only |
| Rejected | `.xlsm`, `.xls`, archives, executables, binary CSV, invalid workbook content |
| Maximum size | 10 MB effective pilot limit |
| Maximum rows | 5,000 data rows |
| Maximum sheets | 20 workbook sheets |
| Maximum columns | 100 columns |
| CSV encodings | UTF-8 / UTF-8 with BOM |
| CSV delimiters | comma, semicolon, tab |

Formula cells are read as inert values only. Server-side import code does not execute formulas, macros, links, Meta requests, or Nova Poshta requests.

## Capability inventory

| Import type | Template | Preview | Mapping | Dry-run | Execute | Duplicates | Logs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Customers | actual via customer mapping/preset | actual | actual | actual | actual | phone / Instagram workspace-local warnings | actual |
| Products | actual via product mapping/preset | actual | actual | actual | actual | SKU workspace-local warnings | actual |
| Product variants | actual via variant mapping | actual | actual | actual | actual | variant SKU workspace-local warnings | actual |
| Inventory | actual via inventory mapping | actual | actual | actual | actual | variant SKU duplicate warnings; stock must be non-negative | actual |
| Product catalog | actual Your Jewelry catalog preset | actual | actual | actual | actual | product SKU and variant SKU warnings | actual |
| Orders history | actual Your Jewelry history preset | actual | actual | actual | actual with historical semantics | order number workspace-local skip/reuse behavior | actual |
| Advertising history | actual CSV/preset | actual | actual | actual | actual manual campaign/metric import | campaign/date workspace-local warnings | actual |
| Shipments | actual mapping only | actual | actual | actual | actual local draft/non-provider rows | order/tracking workspace-local checks | actual |

Unsupported public self-service import types remain deferred; documentation must not imply broad ETL support.

## Duplicate policy

Default pilot policy is `SKIP`/safe warning for existing workspace matches. `UPDATE_EXISTING` is not the default and must not silently overwrite historical records. Blank identifiers are never duplicate keys.

## Templates

- Customers: Ukrainian headers for name/phone/Instagram/city/region; phone or Instagram is recommended for duplicate detection.
- Products and variants: SKU-based matching; archived or foreign-workspace variants are not valid targets.
- Inventory: import physical stock/opening balance through approved inventory fields; negative quantities are rejected.
- Orders history: historical rows do not call delivery providers and do not affect inventory unless the explicit option is enabled.
- Advertising: manual campaign/date metrics only; no Meta Ads API connection.
