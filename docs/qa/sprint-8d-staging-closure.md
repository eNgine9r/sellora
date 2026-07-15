# Sprint 8D — Orders, Inventory & Local Shipments Staging Closure

## Final decision

```text
Sprint 8D — APPROVED
Orders — READY FOR CONTROLLED PILOT
Inventory — READY FOR CONTROLLED PILOT
Local Shipments — READY FOR CONTROLLED PILOT
Controlled guided pilot — GREEN
Public production launch — NOT APPROVED
```

Sprint 8D closes staging/runtime evidence for the existing Orders, Inventory and local Shipments workflows. It does not activate real Nova Poshta provider calls and does not expand the public-production scope.

## Included product changes

- PR #166 — order, inventory and local-shipment operational hardening;
- PR #168 — archived-variant visibility and warning in Inventory;
- PR #169 — synchronous inventory submit lock preventing duplicate stock operations;
- canonical Vercel production deployment: `37eec294ee34e9511a30b40db8b65350798a5f7b`;
- validated backend runtime: `9bf30f3140e6800b33577ef248c7f6c441201613`.

## Gate A — Environment

- canonical frontend reachable: PASS;
- backend `/health`: PASS;
- backend runtime identity available: PASS;
- synthetic OWNER, MANAGER and ANALYST accounts: PASS;
- dedicated QA workspace: PASS;
- credentials and tokens absent from artifacts: PASS.

## Gates B–J — Core runtime

Authoritative workflow run: `29409825368`.

- 44 / 44 checks passed;
- 129 API requests inspected;
- HTTP 5xx: 0;
- Nova Poshta calls: 0;
- Meta Ads calls: 0.

### Reservation and reconciliation

- order quantity `2` reserved exactly `2` units;
- quantity `2 → 4` applied reservation delta `+2`;
- quantity `4 → 1` applied reservation delta `−3`;
- failed increases above available stock left order, items and inventory unchanged;
- variant replacement released Variant A and reserved Variant B atomically;
- archived variants were rejected without partial writes.

### Cancellation, shipment, ship and return

- cancellation released reservation once and did not change physical stock;
- repeated cancellation produced no second inventory/history effect;
- SHIPPED reduced physical stock and reservation once;
- repeated SHIPPED produced no second deduction;
- RETURNED restored physical stock once;
- repeated return produced no second restoration;
- shipment, order link, inventory effects and history committed atomically;
- second active shipment and shipments for cancelled/returned orders were rejected;
- local shipment flow generated no fake TTN and made no provider call.

### PostgreSQL concurrency

Last-unit test started from:

```text
stock = 1
reserved = 0
available = 1
```

Two concurrent order requests returned one success and one safe conflict:

```text
statuses = [409, 201]
successful orders = 1
stock = 1
reserved = 1
available = 0
```

Concurrent order-item edits against the same contested row returned one success and one safe rejection. No overselling, negative availability or `reserved > stock` state was observed.

### RBAC and tenant isolation

- OWNER operational flow: PASS;
- MANAGER allowed operations remained within existing permissions;
- ANALYST GET allowed and mutations denied;
- foreign customer, variant, order, inventory, shipment and history access rejected;
- workspace-scoped reads and writes preserved.

## Gates K–L — Browser and mobile

### Canonical UI matrix

Workflow run: `29412735745`.

- routes: `/orders`, `/inventory`, `/shipments`;
- themes: light and dark;
- viewports: 1366×768, 375×812, 390×844, 430×932 and 768×1024;
- 78 / 78 canonical UI checks passed;
- 31 screenshots captured;
- 1,630 network events inspected;
- horizontal body overflow: 0;
- hidden primary CTA: 0;
- unexpected double-scroll blocker: 0;
- console errors: 0;
- page/runtime exceptions: 0;
- request failures: 0;
- CORS errors: 0;
- unexpected 404/5xx: 0;
- Meta Ads / Nova Poshta calls: 0.

### Workspace switching

Workflow run: `29413020505`.

- 18 / 18 checks passed;
- desktop and mobile order forms closed/reset on Workspace A → Workspace B;
- shipment forms closed/reset;
- inventory form identifiers and reason values cleared;
- old form could not submit after switching;
- Workspace A data did not flash in Workspace B;
- post-switch inventory requests carried Workspace B scope;
- browser/runtime/network/CORS errors: 0.

### Final duplicate-submit proof

Workflow run: `29414891055`.

Two synchronous clicks on the Inventory stock-operation button produced:

```text
inventory POST requests = 1
matching inventory transactions = 1
stock = 5 → 6
reserved = 0
```

Additional results:

- 11 / 11 checks passed;
- browser network events: 110;
- POST requests: 1;
- console/page/request/CORS errors: 0;
- unexpected 404/5xx: 0;
- provider calls: 0;
- synthetic fixture cleanup: stock `0`, reserved `0`, hidden from active Inventory.

## Gate M — Cleanup

Final independent PostgreSQL verification:

```text
active QA8D orders = 0
active QA8D reservations = 0
active QA8D stock = 0
active QA8D shipments = 0
active QA8D products = 0
active QA8D variants = 0
active QA8D customers = 0
active QA8D isolation workspaces = 0
```

Bulk cleanup retained 84 explicit inventory audit transactions. Normal audit/history evidence remains available, while active synthetic business fixtures are absent.

## Issue #134 disposition

Archived zero-stock variants are hidden from default active Inventory. Archived variants with physical stock or reservations remain visible in the operational/history context with an explicit localized warning and cannot be selected for new orders. Historical inventory information is preserved without exposing stale sellable entries.

## Scope boundary

Approved:

- controlled guided pilot;
- Orders operational workflow;
- Inventory reservations and stock effects;
- local Shipment drafts and lifecycle linkage.

Not approved in this closure:

- real Nova Poshta API/TTN validation;
- unrestricted public production launch;
- workflows outside the existing Sprint 8D RBAC and business-rule scope.

## Next stage

`Sprint 8E — Nova Poshta Real Validation`.
