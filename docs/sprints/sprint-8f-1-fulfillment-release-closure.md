# Sprint 8F.1 — Fulfillment Consolidation & Release Closure

Status: **canonical consolidation implemented in repository; not approved for unrestricted production**.

## Canonical architecture

- Retained canonical table: `order_fulfillments`.
- Removed duplicate runtime table through forward migration: `order_fulfillment_operations`.
- Retained canonical repository: `OrderFulfillmentRepository`.
- Retained canonical service: `OrderFulfillmentService`.
- Both `/api/v1/order-fulfillments` and `/api/v1/orders/{order_id}/fulfillment/*` use the same canonical table and service.

## Migration from duplicate journal

Migration `202607180026` extends `order_fulfillments`, maps legacy states to the single state machine, merges rows from `order_fulfillment_operations`, flags deterministic provider/tracking conflicts as `RECONCILIATION_REQUIRED`, creates canonical active-operation/fingerprint indexes, and then drops the duplicate table.

## Inventory lock strategy

Order creation now collects unique variant IDs, sorts them by `product_variant_id`, locks the inventory rows with `SELECT ... FOR UPDATE`, validates availability for all items, then applies reservations atomically.

Existing-order fulfillment locks the order and inventory rows, verifies the existing reservation, and records `reservation_verified=true` without reserving the same items again.

## Provider lifecycle

- Provider writes disabled/readiness errors keep the local shipment safe with TTN pending and do not create false reconciliation.
- Explicit provider success stores tracking/document markers on the canonical fulfillment.
- Ambiguous provider responses set `RECONCILIATION_REQUIRED`, `manual_reconciliation_required=true`, and `blind_retry_blocked=true`.
- Reconciliation calls the existing Nova Poshta durable reconciliation path and never calls provider create.

## Cancellation lifecycle

Local cancellation is handled in the service layer against canonical operation state. Unsupported provider cancellation and inventory-release combinations return safe conflicts rather than pretending provider cleanup happened.

## Finance rules

This consolidation does not introduce full accounting. Draft/TTN-pending fulfillment does not recognize additional revenue or COGS. Existing order/shipment status workflows remain the source of stock-out, delivery, return, and profit recalculation behavior pending full runtime finance evidence.

## Not claimed as complete

The following release gates require external CI/runtime/provider evidence and are **not approved by this repository-only change**:

- GitHub Actions full green run.
- Seeded PostgreSQL 16 migration/concurrency workflow evidence.
- Render runtime commit and Alembic revision verification.
- Vercel production deployment evidence.
- Desktop/mobile browser QA.
- Controlled real Nova Poshta TTN smoke test.
- Provider cleanup and provider-write disabled evidence after the smoke test.
