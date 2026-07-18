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

## GitHub CI status

PR #194 corrected the strict endpoint inventory to the canonical 167-route / 95-mutation API surface and completed the Sprint 8F.1 static, focused, full backend, PostgreSQL and frontend checks successfully.

The repository-hygiene closure replaces overlapping Sprint-named PR workflows with one canonical `Sellora CI` workflow. Permanent required check names are now product-level rather than Sprint-level:

- `Sellora CI / backend-static`
- `Sellora CI / backend-focused`
- `Sellora CI / backend-full`
- `Sellora CI / postgresql-integration`
- `Sellora CI / frontend-production`
- `Sellora CI / security-and-tenant-isolation`
- `Vercel`

Hosted storage and restart-boundary checks remain explicit manual workflows because they require staging credentials and runtime access. They must not block ordinary pull requests through skipped checks.

Detailed audit: `docs/qa/github-actions-workflow-audit.md`.

Repository hygiene decisions: `docs/qa/github-repository-hygiene-closure.md`.

## Not claimed as complete

The following release gates require external runtime/provider evidence and are **not approved by this repository-only change**:

- Render runtime commit and Alembic revision verification.
- Vercel production deployment evidence for the final approved merge commit.
- Desktop/mobile browser QA.
- Controlled real Nova Poshta TTN smoke test.
- Restart durability.
- Provider cleanup and provider-write disabled evidence after the smoke test.
- Resolution or explicit pilot decision for open issues #137, #132 and #131.
