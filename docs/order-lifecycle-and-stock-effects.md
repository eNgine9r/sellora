# Order lifecycle and stock effects — Sprint 8D

## Actual enums

Order statuses: `NEW`, `CONFIRMED`, `SHIPPED`, `DELIVERED`, `COMPLETED`, `RETURNED`, `CANCELLED`.
Payment statuses: `PENDING`, `PAID`, `COD`, `REFUNDED`.

## Transition matrix

| From | To | Stock effect | Reservation effect | History |
| --- | --- | --- | --- | --- |
| NEW | CONFIRMED | none | none | status history once |
| NEW | CANCELLED | none | release reserved items | status history once |
| CONFIRMED | SHIPPED | decrease physical stock once | release reserved items once | status history once |
| CONFIRMED | CANCELLED | none | release reserved items | status history once |
| SHIPPED | DELIVERED | none | none | status history once |
| SHIPPED | RETURNED | restore physical stock once | none | status history once |
| DELIVERED | COMPLETED | none | none | status history once and customer metrics update |
| DELIVERED | RETURNED | restore physical stock once | none | status history once |
| COMPLETED | RETURNED | restore physical stock once | none | status history once |

Repeated same-status requests return the existing order and do not create duplicate stock effects or history.

## Reservation semantics

Order creation reserves requested quantity against each workspace-local active variant. Editing order items reconciles deltas only: increases reserve only the additional quantity, decreases release only the removed quantity, replacement releases the old variant and reserves the new variant.

Archived or inactive variants/products cannot be used in new orders or item edits. Foreign-workspace customer, variant, campaign or inventory references are rejected through workspace-scoped service/repository lookups.

## Edit-order reconciliation

Reservation delta is calculated as `new_qty - old_qty`. Quantity increases reserve only the positive delta, quantity decreases release only the negative delta, variant replacement releases the old variant reservation and reserves the new variant, and a failed edit must leave the order, items, reservations and inventory transactions unchanged.
