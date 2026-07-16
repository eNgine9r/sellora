# Sprint 8F Foundation Audit — Issue #185

Date: 2026-07-16
Scope: PR 1 foundation for validation, addresses, and Nova Poshta provider write permission.

## Alembic head

- Previous repository head before this slice: `202607150022` (`add durable Nova Poshta provider operations`).
- New migration introduced by this slice: `202607160023`.

## Current constraints and indexes observed

- `customer_addresses` is workspace-scoped and soft-delete aware through shared mixins.
- Customer address reads in the CRM completion repository filter by `workspace_id`, `customer_id`, and `deleted_at IS NULL`.
- Shipment creation already preserves the active-shipment rule through repository/service checks and existing database constraints.
- Nova Poshta durable operation uniqueness already exists for idempotency key and `(workspace_id, shipment_id, operation_type)`.

## Query keys and frontend state

- Existing frontend query/service structure remains unchanged in this foundation PR.
- The fulfillment wizard and query-key lifecycle are intentionally deferred to the Sprint 8F UI PR.
- Future wizard city-change behavior must clear warehouse selection in local form state, require the user to select a new warehouse, and submit city ref + warehouse ref + warehouse description atomically; incomplete destination state must not be persisted.

## Existing submit locks

- Existing Nova Poshta TTN creation is routed through the durable backend operation state machine.
- Frontend synchronous submit lock for the new three-step wizard is intentionally deferred to the Sprint 8F UI PR.

## Current Nova Poshta payload

- The active adapter is `NovaPoshtaProviderShipmentService`.
- Before this slice, payload construction used shipment recipient phone as stored and destination descriptions from shipment fields.
- COD backward-delivery payload correction is intentionally deferred to the Sprint 8F fulfillment backend/provider-payload PR.

## Current inventory reservation logic

- Existing order/inventory behavior remains unchanged in this foundation PR.
- Deterministic row locking and top-level fulfillment reservation orchestration are intentionally deferred to the Sprint 8F fulfillment backend PR.

## Current active-shipment constraint

- Shipment service checks for an active shipment before creating or updating a shipment for an order.
- Existing database-level active-shipment protection is preserved.

## Current customer address endpoints

- `GET /api/v1/customers/{customer_id}/addresses`
- `POST /api/v1/customers/{customer_id}/addresses`
- `PUT /api/v1/customers/{customer_id}/addresses/{address_id}`
- `DELETE /api/v1/customers/{customer_id}/addresses/{address_id}`

## Existing durable TTN tests observed

- `backend/tests/integrations/nova_poshta/test_durable_ttn_workflow.py`
- `backend/tests/test_nova_poshta.py`
- `backend/tests/integrations/nova_poshta/test_real_provider_payload.py`

## Foundation decisions implemented

- Ukrainian phone normalization has one backend source of truth in `app.utils.phone`.
- Customer, customer address, and shipment schemas normalize supplied phone values without backfilling ambiguous historical values.
- Nova Poshta address refs can be persisted on customer addresses.
- One active default address is enforced with a PostgreSQL partial unique index after repairing duplicate active defaults with a set-based `row_number()` CTE.
- Provider write permission is stored on the Nova Poshta integration connection and defaults to disabled.
- Effective provider writes require environment capability, connected credential, sender settings, verified connection, and workspace permission.

## Deferred work

- Real PostgreSQL migration execution evidence is required in CI/staging or a local PostgreSQL service; this container does not expose a PostgreSQL server.
- `OrderFulfillmentService`, `order_fulfillment_operations`, and orchestration endpoint.
- Inventory row locking inside fulfillment.
- Canonical directory verification before provider document creation.
- COD backward-delivery provider payload contract.
- Three-step frontend wizard and responsive/browser evidence.
