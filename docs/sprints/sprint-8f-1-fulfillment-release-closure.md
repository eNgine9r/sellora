# Sprint 8F.1 — Fulfillment Release Closure

Status: **implemented foundation, not approved for unrestricted production**.

## Implemented in this change

- Added the durable `order_fulfillment_operations` journal for existing-order fulfillment orchestration.
- Added workspace-scoped idempotency protection with a unique `(workspace_id, idempotency_key)` contract.
- Added PostgreSQL partial uniqueness for one active fulfillment operation per workspace/order.
- Added a completed fingerprint uniqueness guard to prevent duplicate durable results for the same canonical request.
- Added backend prepare, execute, status, reconcile, and cancel endpoints under `/api/v1/orders/{order_id}/fulfillment`.
- Added deterministic request fingerprinting that includes workspace/order identity, normalized recipient/delivery/payment fields, and stable ordered order items.
- Added fulfillment execution boundaries that create/reuse one active shipment and block blind Nova Poshta provider creation unless the controlled production gate is completed.
- Added row-locking repository support for inventory rows in stable `product_variant_id` order.

## Not claimed as complete

The following release gates require external CI/runtime/provider evidence and are **not approved by this repository-only change**:

- GitHub Actions full green run.
- PostgreSQL 16 migration/concurrency workflow evidence.
- Render runtime commit and Alembic revision verification.
- Vercel production deployment evidence.
- Desktop/mobile browser QA.
- Controlled real Nova Poshta TTN smoke test.
- Provider cleanup and provider-write disabled evidence after the smoke test.

## Manual branch protection action

Codex cannot configure GitHub branch protection from this environment. Before merging to `main`, configure required checks for:

- Sprint 8F.1 focused backend.
- Full backend suite.
- PostgreSQL migration/concurrency gate.
- Security/tenant isolation.
- Frontend production gate.
- Vercel deployment.

Require pull requests, up-to-date branches, resolved conversations, and no ordinary bypass.
