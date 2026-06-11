# Sprint 1.3 Products, Variants, and Inventory

Sprint 1.3 introduces Sellora catalog and inventory management without implementing Orders.

## Domain entities

- `Product`: workspace-scoped, soft-deletable product with SKU, description, active flag, and images.
- `ProductVariant`: workspace-scoped, soft-deletable variant with variant SKU, color, size, and price.
- `ProductImage`: workspace-scoped, soft-deletable product image metadata.
- `Inventory`: workspace-scoped, soft-deletable stock record automatically created for each variant.
- `InventoryTransaction`: workspace-scoped, soft-deletable stock movement history.

## Business rules

- Variant uniqueness is enforced by `(product_id, color, size)`.
- Creating a product variant automatically creates the corresponding inventory record.
- Low stock is detected when `stock_quantity <= minimum_quantity`.
- Inventory transaction types are `STOCK_IN`, `STOCK_OUT`, `RESERVE`, `UNRESERVE`, `RETURN`, and `ADJUSTMENT`.
- Inventory transactions update inventory quantities and write audit logs.

## API

- `/api/v1/products`
- `/api/v1/products/{product_id}`
- `/api/v1/products/{product_id}/images`
- `/api/v1/products/variants`
- `/api/v1/products/variants/{variant_id}`
- `/api/v1/inventory`
- `/api/v1/inventory/{inventory_id}`
- `/api/v1/inventory/{inventory_id}/transactions`
- `/api/v1/inventory/transactions`
