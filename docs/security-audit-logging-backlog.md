# Security Audit Logging Backlog

This backlog records audit-log gaps found during Sprint 7E / 7E.1. It is intentionally documentation-only: no migration, schema change, new table, or destructive data operation was added in Sprint 7E.1.

| Event | Current state | Risk | Required future action |
| --- | --- | --- | --- |
| Role change | Partial — workspace-user role endpoint exists; audit coverage must be verified end-to-end against persistent audit logs. | High: unauthorized privilege changes need reliable traceability. | Add/verify service-level audit event `WORKSPACE_MEMBER_ROLE_CHANGE` with actor, target user, old role, new role, workspace ID, timestamp. |
| Membership creation | Partial — user creation/membership endpoint exists; audit coverage must be verified. | High: unauthorized member creation expands workspace access. | Add/verify `WORKSPACE_MEMBER_CREATE` audit event without storing temporary passwords. |
| Membership deactivation | Partial — deactivation endpoint exists; audit coverage must be verified. | High: access removal impacts operations and incident review. | Add/verify `WORKSPACE_MEMBER_DEACTIVATE` audit event with actor and target user only. |
| Workspace settings changes | Partial — workspace update is OWNER-only; audit coverage must be verified. | Medium: currency/timezone/slug/name changes affect reporting and access context. | Add/verify `WORKSPACE_SETTINGS_UPDATE` with old/new safe fields only. |
| Inventory mutations | Partial — inventory transaction records exist and should be treated as operational audit evidence; audit-log parity must be verified. | High: stock movement affects order fulfillment and profit. | Standardize audit events for stock increase/decrease/adjust/reserve/release/return. |
| Order status changes | Partial — status history exists; audit-log parity must be verified. | High: status changes affect shipment, inventory and revenue recognition. | Verify every order status transition writes actor, old status, new status and workspace ID. |
| Finance adjustments | Partial — finance adjustment endpoints exist; audit coverage must be verified. | High: manual financial changes affect net profit. | Add/verify `FINANCE_ADJUSTMENT_CREATE/UPDATE/ARCHIVE` audit events with safe amount/category/reference fields. |
| Profit-affecting changes | Partial — profit is calculated from orders/items/expenses; full audit chain must be verified. | High: unexplained profit changes reduce user trust and complicate incident response. | Define a profit-impact audit policy spanning order items, product costs, ad costs, shipping/COD fees and finance adjustments. |
| Critical archive actions | Partial — soft-delete/archive actions exist across modules; consistent audit naming is not yet guaranteed. | Medium/High depending on entity: archives can hide operational records. | Standardize `*_ARCHIVE` audit events across leads, customers, orders, products, variants, shipments, campaigns and adjustments. |

## Secret-safety rule

Audit events must never store passwords, password hashes, access tokens, refresh tokens, API keys, authorization headers, database URLs, provider raw payloads, or encrypted-secret plaintext.
