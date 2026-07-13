# Import Security and Data Handling — Sprint 8C

## Workspace isolation

Every import route uses the authenticated user plus `X-Workspace-ID` dependency. Import jobs, logs, preview, dry-run, execute, and entity lookups are scoped by server-side workspace context. Uploaded files and mappings cannot choose a target workspace.

Workspace switch behavior on the frontend clears selected file/job, sheet, preview, mapping, validation report, dry-run report, execute confirmation state, and result state before refetching logs for the new workspace.

## RBAC

- OWNER: upload, preview, map, validate, dry-run, execute, and view logs.
- MANAGER: not granted import execution in the current hardened pilot policy unless backend permissions are explicitly changed later.
- ANALYST: cannot upload or execute imports through direct API calls; frontend copy may explain templates/logs only when access exists.

## File safety

`.xlsx` uploads must be valid ZIP-based workbooks. `.csv` uploads must be text-like UTF-8. Macro-enabled spreadsheets and executables are rejected. Files are stored under the workspace/job import storage path and source files are gitignored.

## Dry-run and execute safety

Dry-run is mandatory before execute. The dry-run signature is derived from job, workspace, import type, sheet, mapping, and options for audit evidence. Execute also re-parses and re-validates rows before writing, and refuses execution if the job has not passed a successful dry-run.

Default import execution remains all-or-nothing in policy. Historical order imports are documented as historical data and must not call Meta or Nova Poshta. Inventory effects are opt-in for historical orders and remain visible to the user.

## PII and logging

Import logs record safe row status and summaries only. Do not commit uploaded customer/order files, production exports, real phone numbers, real addresses, raw credentials, API tokens, database URLs, or provider secrets.

## Error report export

CSV error reports must be UTF-8 with BOM and escape values beginning with `=`, `+`, `-`, or `@` to prevent spreadsheet formula injection.
