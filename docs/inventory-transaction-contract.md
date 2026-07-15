# Inventory transaction contract — Sprint 8D

Invariant:

```text
available_quantity = stock_quantity - reserved_quantity
stock_quantity >= 0
reserved_quantity >= 0
reserved_quantity <= stock_quantity
```

Supported transaction types remain backend enums: `STOCK_IN`, `STOCK_OUT`, `RESERVE`, `UNRESERVE`, `RETURN`, `ADJUSTMENT`.

| Type | Physical stock | Reserved stock | Used by |
| --- | --- | --- | --- |
| STOCK_IN | increases | unchanged | manual restock/import-safe stock-in |
| STOCK_OUT | decreases available physical stock | unchanged | shipment deduction/manual stock-out |
| RESERVE | unchanged | increases | order creation/edit increase |
| UNRESERVE | unchanged | decreases | cancellation/edit decrease/shipment release |
| RETURN | increases | unchanged | returned shipped/delivered order |
| ADJUSTMENT | sets physical stock | unchanged | manual correction; cannot fall below reserved |

Low stock uses available quantity (`stock_quantity - reserved_quantity`) against `minimum_quantity`.

Issue #134 policy: archived zero-stock/unreserved variants are hidden from the default active inventory list; archived variants with stock or reservations remain visible until operationally resolved and cannot be selected for new orders.
