# Sprint 8F.1 Controlled Provider Smoke Test

Status: **not executed**.

Run this only after all CI, migration, deployment, and browser QA gates are green.

## Sanitized evidence to capture

- Commit SHA.
- Operation ID hash.
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
