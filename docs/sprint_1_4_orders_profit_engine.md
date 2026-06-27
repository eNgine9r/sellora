# Sprint 1.4 Orders and Profit Engine

Sprint 1.4 adds Orders without implementing shipments or payments as standalone modules.

## Domain entities

- `Order`: workspace-scoped, soft-deletable order with generated order number, status, payment status, revenue/cost fields, and net profit.
- `OrderItem`: workspace-scoped, soft-deletable line item linked to a product variant.
- `OrderStatusHistory`: workspace-scoped, soft-deletable status audit trail.

## Business rules

- Order numbers are generated as `ORD-YYYY-000001`.
- Creating an order reserves inventory.
- Shipping an order unreleases reservation and decreases stock.
- Cancelling an unshipped order returns reservation.
- Returning a shipped/delivered/completed order restores stock.
- Net profit is `revenue - product_cost - ad_cost - shipping_cost - cod_fee - other_cost`.
- Completing an order updates customer `total_orders`, `total_spent`, and `last_order_at`.

## Dashboard aggregates

- Orders today.
- Revenue today.
- Profit today.
