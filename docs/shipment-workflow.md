# Shipment Workflow — Sprint 3.1

Sellora keeps order status and shipment status related but separate. Creating a shipment or a Nova Poshta TTN does **not** automatically complete an order.

## Operational flow

1. Create or select a customer.
2. Create an order linked to that customer.
3. Create a shipment from the order.
4. Confirm recipient name, phone, city, warehouse, declared value, COD and shipping cost.
5. Create a Nova Poshta TTN when the API key and sender settings are ready.
6. Copy the TTN number for Nova Poshta cabinet workflows.
7. Sync delivery status when TTN exists and the Nova Poshta service is available.

## TTN behavior

- TTN creation is allowed only for a workspace-scoped shipment linked to an order and customer.
- TTN creation validates recipient name, phone, city, warehouse, declared value and sender settings.
- Duplicate TTN creation is blocked; existing tracking/document numbers remain visible.
- TTN copy is supported in the UI.
- Printable/downloadable TTN documents are a known limitation for this sprint; users can copy the TTN and open it in the Nova Poshta account.

## Status behavior

- Internal shipment status remains the primary status badge.
- Nova Poshta external status is shown as helper text when available.
- Status sync requires an existing TTN and returns a safe localized message if unavailable.
- TTN creation sets shipment status to `CREATED`; it does not complete the order.
- Later shipment transitions may update shipment/order delivery progress according to existing service rules, but order completion remains separate from TTN creation.

## RBAC and workspace safety

- `OWNER` and `MANAGER` can create/update shipments, create TTNs and sync status through existing backend guards.
- `ANALYST` can view shipments but cannot mutate them.
- Shipment, order, customer and Nova Poshta credential operations are workspace-scoped.
- Audit logs store safe action metadata and must not contain raw API keys or raw Nova Poshta payloads.
