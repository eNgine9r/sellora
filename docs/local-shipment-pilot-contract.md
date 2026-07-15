# Local shipment pilot contract — Sprint 8D

Sprint 8D validates only local/manual shipment workflow. It does not create real Nova Poshta TTNs, does not poll delivery status, and does not require live Nova Poshta credentials.

## Workflow

Order → local shipment draft → local/manual status update → status visibility.

Shipment statuses: `DRAFT`, `CREATED`, `IN_TRANSIT`, `ARRIVED`, `DELIVERED`, `RETURNED`, `CANCELLED`.

## Rules

- Shipment order must belong to the active workspace.
- Shipment customer must match the order customer.
- Cancelled or returned orders cannot receive new shipments.
- Only one active shipment may exist per order; cancelled shipments are not active.
- Non-draft shipments require a tracking number, but local drafts may have no TTN.
- No provider request is made by the local draft/status flow.
- Repeating the same shipment status update is idempotent and does not duplicate order transitions.

Preferred UI language: `Ручне відправлення` or `Чернетка — не передано перевізнику` when no provider action occurred.

## One-active-shipment rule

The one-active-shipment rule is enforced before creating a local shipment draft: a second active shipment for the same order is rejected, the existing shipment remains unchanged, and provider calls = 0.
