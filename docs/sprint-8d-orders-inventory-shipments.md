# Sprint 8D — Orders, Inventory & Shipments Pilot Polish

## Existing capability inventory

Audited `OrderService`, `OrderRepository`, inventory transactions, `InventoryService`, `ShipmentService`, shipment repository, order status history, current frontend Orders/Inventory/Shipments pages, workspace-aware query keys, role checks and localization surfaces.

## Actual order/payment/status enums

Order: `NEW`, `CONFIRMED`, `SHIPPED`, `DELIVERED`, `COMPLETED`, `RETURNED`, `CANCELLED`.
Payment: `PENDING`, `PAID`, `COD`, `REFUNDED`.
Shipment: `DRAFT`, `CREATED`, `IN_TRANSIT`, `ARRIVED`, `DELIVERED`, `RETURNED`, `CANCELLED`.
Inventory: `STOCK_IN`, `STOCK_OUT`, `RESERVE`, `UNRESERVE`, `RETURN`, `ADJUSTMENT`.

## Order transition matrix

See `docs/order-lifecycle-and-stock-effects.md`.

## Reservation semantics

Order creation reserves active workspace-local variants once. Item edits reconcile only deltas. Cancellation before shipment releases reservation. Shipment release/deduction occurs once. Return restores physical stock once.

## Deduction/release/return semantics

`CONFIRMED -> SHIPPED` releases reservation and deducts stock. `NEW/CONFIRMED -> CANCELLED` releases reservation only. `SHIPPED/DELIVERED/COMPLETED -> RETURNED` restores stock once.

## Edit-order reconciliation

Quantity increase reserves delta, quantity decrease releases delta, variant replacement releases old reservation and reserves new reservation atomically in the service flow.

## Concurrency behavior

No migration or new queue was introduced. Existing transactional checks prevent reserving beyond available stock in a single request; a true PostgreSQL last-unit concurrency proof remains a staging/runtime requirement.

## Inventory transaction contract

See `docs/inventory-transaction-contract.md`.

## Issue #134 disposition

Implemented smallest safe policy: archived zero-stock/unreserved variants are hidden from the default inventory list, while archived variants with stock or reservations remain visible until resolved. Archived variants cannot be used in new orders.

## Shipment local workflow

See `docs/local-shipment-pilot-contract.md`. Local shipment drafts do not call Nova Poshta and do not fabricate TTNs.

## One-active-shipment rule

ShipmentService rejects a second non-cancelled shipment for the same order and leaves the existing shipment unchanged.

## RBAC

OWNER and MANAGER remain enabled for daily operational mutations according to current route policy. ANALYST remains read-only; mutation denial is covered by existing and Sprint 8D tests.

## Workspace isolation

Orders, inventory, transactions and shipments remain scoped by `workspace_id`; cross-workspace customer, variant, inventory, order and shipment references are rejected by service/repository lookups.

## Atomicity and rollback

Service validation prepares variants/inventory before mutating records; failed item edits preserve existing items and reservations. Full database rollback proof for controlled failures remains a staging/runtime gate.

## Browser/mobile result

Not executed in this environment because no staging/browser runner or role credentials were available.

## Console/network result

Not executed against staging. No Meta or Nova Poshta calls were added.

## Staging scenario matrix

Scenarios A–J from the Sprint 8D brief are documented for staging execution in `docs/pilot-operations-guide.md`; runtime evidence remains pending.

## Cleanup

Synthetic QA cleanup requirements are documented in the pilot guide. No synthetic runtime data was created locally.

## Issues found and fixed

- Added explicit order transition validation to prevent unsafe direct transitions.
- Enforced active product/variant selection for order creation/editing.
- Updated low-stock semantics to use available quantity.
- Applied Issue #134 default inventory visibility policy.
- Prevented local shipment creation for cancelled/returned orders.
- Cleared order/inventory/shipment selected state and forms on workspace switch.

## Remaining limitations

Real Nova Poshta TTN creation/status sync remains Sprint 8E. Finance deep validation remains Sprint 8F. Staging controlled-write/browser evidence is pending.

## Sprint status

Sprint 8D — BLOCKED ⚠️ for final approval until staging controlled-write matrix, browser/mobile QA and cleanup evidence are collected.

## Pilot recommendation

Controlled guided pilot remains GREEN. Operations pilot hardening is locally implemented, but full Sprint 8D approval requires staging evidence.
