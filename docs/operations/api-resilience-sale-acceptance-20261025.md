# API resilience and controlled sale — 25 October 2026

## Scope
Issue #266 readiness evidence and the authenticated Direct → Lead → Customer →
Order → shipment preparation path. No live customer, order, inventory, payment,
provider document or outbound-message writes are part of this acceptance.

## Reproduced defects
1. With a full SQLAlchemy pool, old readiness remained healthy. Added independent
   one-second process sampling: 10 seconds of full capacity or event-loop lag >=1s
   returns 503 with bounded reason codes; a sampler older than 5s is degraded.
   A single loop scheduling pause >=10s counts as an existing long stall.
   Healthy samples clear pressure. Health never checks out a DB connection.
2. An authenticated PostgreSQL canary created an order from a specified Direct
   conversation but left linked_order_id empty (SOURCE_DIRECT_ORDER_LINK_MISSING).
   Fulfillment now calls the existing customer/lead linkage service before the
   same business transaction commits; idempotent replays do not link twice.
3. The canonical prepare API raised AttributeError on provider.value because
   its request model used str while the service expected ShipmentCarrier.
   The request now uses the existing carrier enum, preserving JSON enum values.

## Verification
- Original focused baseline: 14 passed.
- New readiness suite failed before implementation (14 failures).
- Readiness/health/worker checks: 21 passed after implementation.
- Full offline backend suite: 640 passed, 19 skipped (PostgreSQL-specific suites
  require a real DB and run in the PostgreSQL CI job).
- Disposable PostgreSQL 17, Alembic 046, actual cookie-session login and RBAC:
  lead ensure replay, customer dedup, fulfillment replay, Direct source link,
  stock 5 / reserved 1, order confirmation, preparation READY, analyst and
  cross-workspace denials. No external network, real token or customer involved.
- The canary is added to the existing PostgreSQL CI job in an empty, separately
  named disposable database, without overriding authentication dependencies.
- The local full-suite runner must mount the repository parent, not backend
  alone: two existing tests inspect .gitignore and a frontend source file.

## Operations
- /health remains a compatible deployment identity endpoint.
- /health/live proves HTTP/event-loop responsiveness without DB/thread checkout.
- /health/ready reports worker failure/stall, sustained pool/loop pressure or
  stale sampling; it is local process telemetry, not proof of DB reachability.
- Do not use transient readiness failure as an automatic restart trigger without
  grace and a separate liveness check. A DB outage should not cause a restart storm.
- Historical 20 October hang root cause remains unproven. Keep #266 open; point
  probes and simulated failures do not establish 48-hour uptime.
- Release only after required CI, isolated canary and healthy candidate smoke.
  Preserve the existing immutable image as rollback; no schema migration needed.

## Remaining provider acceptance
A real inbound Meta webhook, carrier account/sender readiness, one explicitly
approved real TTN and actual carrier reconciliation still require provider
acceptance. Local shipment preparation is not a provider-created document.
No customer message, real order, ad campaign or payment is auto-created by QA.
