# Sprint Dd.5 — Inventory & Shipments Redesign QA

## Pre-implementation audit

### Inventory contract

- Route inspected: `frontend/src/app/inventory/page.tsx`.
- API/service hooks inspected: `fetchInventory`, `fetchInventoryTransactions`, `createInventoryTransaction`, `updateInventory`, `fetchProducts`, and `fetchProductVariants` from `frontend/src/services/products.ts`.
- Frontend model inspected: `Inventory` exposes `stock_quantity`, `reserved_quantity`, `incoming_quantity`, `minimum_quantity`, `is_low_stock`, `created_at`, and `updated_at`; relations are resolved through `product_variant_id` to variants/products.
- Available stock is represented in the UI as `stock_quantity - reserved_quantity`, matching the existing frontend contract fields and not changing backend calculations.
- Low-stock state uses the existing `is_low_stock` flag and `minimum_quantity`; out-of-stock is a UI state for `stock_quantity <= 0`.
- Transaction history uses real `InventoryTransaction` rows with `transaction_type`, `quantity`, previous/new stock/reserved fields, actor, reason, reference fields, and timestamp.
- Adjustment flow remains the existing `createInventoryTransaction` mutation; threshold editing remains the existing `updateInventory` mutation.
- Current inventory list and transactions are returned as arrays by the existing frontend service; no new backend summary endpoint or all-page fetch loop was introduced.
- OWNER and MANAGER keep mutation controls; ANALYST remains read-only through the existing role check and backend authorization.

### Shipments contract

- Route inspected: `frontend/src/app/shipments/page.tsx`.
- API/service hooks inspected: `fetchShipments`, `fetchShipmentSummary`, `createShipment`, `updateShipment`, `changeShipmentStatus`, and `deleteShipment` from `frontend/src/services/shipments.ts`.
- Frontend model inspected: `Shipment` exposes order/customer relations, carrier, status, tracking number, Nova Poshta document fields, recipient/city/warehouse fields, delivery cost/COD/declared value, notes, sync timestamp, and lifecycle timestamps.
- Shipment statuses remain backend enum values: `DRAFT`, `CREATED`, `IN_TRANSIT`, `ARRIVED`, `DELIVERED`, `RETURNED`, `CANCELLED`; UI labels are localized only on the frontend.
- Shipment summary uses the existing shipment list and existing summary endpoint fields where available (`in_transit_count`, `delivered_today`, `returned_this_month`). No fake tracking, live sync, or connection state was added.
- Nova Poshta functionality remains delegated to the existing `NovaPoshtaShipmentPanel`, `ShipmentForm`, TTN copy actions, and service mutations; no provider credentials or raw secrets are displayed.
- OWNER and MANAGER keep create/edit/archive/status controls; ANALYST remains read-only through the existing role check and backend authorization.

## Implementation decisions

- Inventory and Shipments now use `WorkspacePage`, `WorkspaceHeader`, `CompactSummary`, `WorkspaceSplitView`, and `EntitySidePanel` at route level.
- Desktop detail panels are embedded right-side sibling columns. They do not use a desktop backdrop, body lock, or modal focus trap.
- Mobile/tablet detail behavior is inherited from `EntitySidePanel`, which renders the existing modal `Drawer` fallback below `lg`.
- Pagination is below the Inventory and Shipments list content, following the Dd.4.4 list-page pattern.
- Five-card summaries explicitly use `layout="five-balanced"`.
- Inventory quantities are displayed as separate on-hand, reserved, and available values in summaries, desktop rows, mobile cards, and detail panels.
- Shipments do not claim live tracking or connected Nova Poshta state unless existing data/actions provide it; unavailable sync states remain truthful.

## Page layouts

### Inventory

1. Compact workspace header with real Adjust stock action for editors.
2. Five-card stock summary: total stock, available, reserved, low stock, out of stock.
3. Stock/Transactions tabs and compact filters.
4. `WorkspaceSplitView` with table/mobile cards on the left and inventory detail on the right.
5. Bottom pagination under the inventory list.
6. Real transaction adjustment/history section when the Transactions tab is active.

### Shipments

1. Compact workspace header with real Create shipment action for editors.
2. Five-card shipment summary: all, ready, in transit, delivered, problems/returned.
3. Compact search/status/carrier/TTN filters.
4. `WorkspaceSplitView` with shipment table/mobile cards on the left and shipment detail on the right.
5. Bottom pagination under the shipment list.
6. Existing create, edit, archive, TTN, status and Nova Poshta flows preserved.

## Manual QA matrix

Authenticated browser QA is still required for:

- `/inventory` and `/shipments` in light and dark themes.
- Desktop: 1280×800, 1366×768, 1440×900, 1536×1024, 1920×1080.
- Tablet/mobile: 1024×768, 768×1024, 430×932, 390×844, 375×812.
- Smoke routes: `/orders`, `/products`, `/dashboard`.
- Inventory flows: filters, sorting, pagination, details, transaction tab, adjust stock, threshold edit, workspace switch, role visibility.
- Shipment flows: filters, pagination, details, create/edit/archive, TTN actions, status actions, Nova Poshta panel, workspace switch, role visibility.

## Remaining limitations

- Inventory and shipment summary values use the currently loaded workspace arrays and existing summary endpoint fields. No new backend aggregate endpoints were introduced in this frontend-only sprint.
- Browser-authenticated visual QA was not executed in this coding environment and must be completed before full approval.
