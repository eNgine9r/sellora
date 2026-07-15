# Sprint 8D — Orders, Inventory & Local Shipments Staging Closure

## Status

`HOLD — canonical duplicate-submit proof pending`

This document records sanitized staging evidence for Sprint 8D. It also acts as a docs-only deployment trigger so the canonical Vercel staging alias receives the merged inventory duplicate-submit guard from PR #169.

## Included product commits

- PR #166 — order, inventory and local-shipment operational hardening;
- PR #168 — archived-variant warning in Inventory;
- PR #169 — synchronous inventory submit lock preventing duplicate stock operations.

## Completed gates

### Core runtime

- 44 / 44 checks passed;
- real PostgreSQL last-unit concurrency passed;
- concurrent order-item reconciliation passed;
- cancel, ship and return stock effects passed;
- repeated lifecycle requests produced no second stock effect;
- shipment uniqueness and local-provider isolation passed;
- RBAC and cross-workspace isolation passed;
- external Nova Poshta and Meta provider calls: 0.

### Canonical browser/mobile UI

- `/orders`, `/inventory`, `/shipments` checked in light and dark themes;
- viewports: 1366×768, 375×812, 390×844, 430×932 and 768×1024;
- 78 canonical UI checks passed;
- 31 screenshots captured;
- 1,630 browser network events inspected;
- unexpected console, page, request, CORS, 404 and 5xx errors: 0;
- provider calls: 0.

### Workspace switching

- 18 / 18 checks passed;
- desktop and mobile forms close/reset during Workspace A → Workspace B;
- stale inventory identifiers and reason values are cleared;
- an old form cannot submit after switching;
- Workspace A data does not flash in Workspace B;
- post-switch inventory requests contain Workspace B scope.

### Cleanup

Post-closure read-only verification:

- active QA8D orders: 0;
- active QA8D reservations: 0;
- active QA8D stock: 0;
- active QA8D shipments: 0;
- active QA8D products, variants, customers and isolation workspaces: 0;
- cleanup audit inventory transactions retained: 84.

## Remaining gate

The merged PR #169 frontend bundle must be visible through the canonical staging alias. A narrow browser probe must then prove that two synchronous clicks generate:

- one inventory POST;
- one inventory transaction;
- one stock side effect.

Sprint 8D remains on HOLD until that proof passes.

## Scope boundary

This closure does not activate real Nova Poshta provider calls and does not approve unrestricted public production launch.
