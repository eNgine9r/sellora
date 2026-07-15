# Nova Poshta security and secrets — Sprint 8E

## Credential safety

- Nova Poshta API keys are handled through the existing encrypted integration credential mechanism.
- Settings responses return `masked_api_key`, never the raw saved API key.
- Provider write operations require the backend server-side `STAGING_NOVA_POSHTA_ALLOW_WRITES=true` flag or an explicit service-level test override.
- Read-only discovery and status lookup may run when the workspace integration is configured.
- Provider write denial returns a safe application error and does not call the provider.

## RBAC and workspace scope

- Settings configuration and validation remain OWNER-only through existing API dependencies.
- City/warehouse lookup, TTN creation and manual status sync require MANAGER-or-higher through existing route dependencies.
- ANALYST direct provider mutations remain denied by backend RBAC.
- Integration connections, credentials and shipments are all queried by `workspace_id`.

## PII and logging

Audit events must not include the API key, full provider payload, full recipient address or complete phone number. Sprint 8E stores only the supported shipment fields: TTN/document number, provider document ref, raw provider status and sync timestamp.
