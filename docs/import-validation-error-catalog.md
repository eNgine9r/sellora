# Import Validation Error Catalog — Sprint 8C

Validation issues use English backend codes/fields and localized UI messages. A row issue should include row number, source column/field, severity, message, and a masked value preview when a value is sensitive.

## Severity levels

| Severity | Meaning | Import behavior |
| --- | --- | --- |
| `ERROR` | Blocking validation problem | Execute disabled; all-or-nothing import must not write business records |
| `WARNING` | Non-destructive duplicate/normalization concern | User may continue after review when no errors exist |
| `INFO` | Safe normalization note | Non-blocking |

## Required catalog

| Code / condition | Severity | Examples |
| --- | --- | --- |
| `REQUIRED_MAPPING_MISSING` | ERROR | Missing customer identifier, missing variant SKU, missing metric date |
| `REQUIRED_VALUE_MISSING` | ERROR | Empty required row value |
| `INVALID_NUMBER` | ERROR | Text in quantity, spend, revenue, price, cost |
| `NEGATIVE_QUANTITY` | ERROR | Negative stock, quantity, spend, revenue where prohibited |
| `INVALID_DATE` | ERROR | Unsupported date format |
| `INVALID_ENUM` | ERROR | Unknown status/payment/platform value |
| `DUPLICATE_IN_FILE` | WARNING/ERROR by type | Repeated inventory SKU or campaign/date in the same file |
| `DUPLICATE_IN_WORKSPACE` | WARNING | Existing customer/product/variant/campaign/metric in current workspace |
| `UNKNOWN_REFERENCE` | ERROR | Shipment order number or variant SKU not found in current workspace |
| `FOREIGN_WORKSPACE_REFERENCE` | ERROR | Any reference that resolves outside active workspace is rejected by workspace-scoped lookups |
| `FORMULA_INJECTION_RISK` | INFO/WARNING | Exported CSV values beginning with `=`, `+`, `-`, `@` are escaped |
| `UNSUPPORTED_FILE_TYPE` | ERROR | `.xlsm`, `.xls`, executable, archive, binary content |
| `DUPLICATE_HEADERS` | ERROR | Ambiguous source headers after normalization |
| `ROW_LIMIT_EXCEEDED` | ERROR | More than 5,000 rows |

Sensitive values such as phone, email, address, payment details, tokens, database URLs, and raw stack traces must not be exported in error reports or logs.
