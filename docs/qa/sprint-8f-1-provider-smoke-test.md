# Sprint 8F.1 Controlled Provider Smoke Test

Status: **not executed**.

Run this only after all CI, seeded PostgreSQL migration, deployment, and browser QA gates are green.

## Required canonical assertions

- One canonical `order_fulfillments` row.
- One shipment.
- One Nova Poshta durable provider operation maximum.
- One provider create call maximum.
- Repeat request returns the stored canonical result.
- Reconcile calls provider reconciliation, not provider create.

## Sanitized evidence to capture

- Commit SHA.
- Fulfillment ID hash.
- Shipment ID hash.
- Document ref hash.
- Masked/hash tracking number.
- Provider create call count.
- Durable result reuse count.
- Runtime process start timestamp.
- Migration revision.
- Write gate state before and after the test.
- Cleanup status.

## Safety requirements

- Do not log API keys.
- Do not expose sender refs.
- Do not use real customer PII.
- Do not create multiple documents.
- Keep provider writes enabled only during the test window.
- Return provider writes to disabled state after cleanup.
