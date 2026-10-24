# Raspberry backend source parity — 2026-10-24

**Purpose:** safely reconcile the code in the running Sellora Raspberry Pi
backend with the reviewed Git repository before releasing Direct → TTN → Order
(PR #327).

## Provenance and scope

Read-only source snapshot from the **running** container
`sellora-rpi-backend-1` using `docker cp`. Runtime image:
`sellora-backend:meta-fx-direct-attribution-20261024`. GitHub comparison
base: `main@9edcb357`. Only Python source under `backend/app` has been
copied into this branch; no production data, credentials, volumes or secrets.

The initial full recursive comparison found **52 changed/new application Python
files** (38 modified, 14 newly tracked). This includes the out-of-band
private-media service, asynchronous worker isolation, health readiness /
liveness telemetry, restricted CORS, and historical Direct/Nova Poshta
operations. Files not changed remain as in the GitHub base.

## Explicit exclusions

- `backend/alembic/versions/202610230044_cod_payment_evidence.py`:
  **do not replace the repository's safer migration** with the deployed
  historical version. The latter revokes from Supabase-specific roles without
  checking their existence. Repository code checks optional roles for
  PostgreSQL 16/17 compatibility. Live database already executed migration 044.
- Operator-only scripts from the live container have **not** been imported:
  `backfill_direct_media.py`, `backfill_np_order_amounts.py`,
  `reconcile_nova_archive.py`, `recover_direct_historical_amounts.py`,
  `start_raspberry.py`. They need independent review, validation and
  explicit permission before any use. They are not required by the repository
  Dockerfile startup command.
- **No changes** to live database, Compose config, running containers,
  shipping, payment, inventory, or customer data.

## Release gates — all mandatory

1. Review the full Python diff for removed business invariants and for secrets.
   The copied source is an out-of-band operational snapshot, **not**
   pre-approved implementation or evidence of functional correctness.
2. Pass GitHub CI (full backend/security/tenant suite, PostgreSQL integration,
   frontend typecheck/build where appropriate).
3. Verify unchanged cookie/session authentication, workspace isolation, RBAC,
   CORS and OAuth redaction; check that a **single** Meta worker processes
   events and outbound auto-send remains disabled.
4. Run PostgreSQL **17** disposable canary from schema 045 to additive
   migration 046, with optional Supabase role checks and no live DB access.
   Assert new relation's RLS, FK/unique constraints, and migration head.
5. Compare the final candidate built ARM64 image source and startup behavior
   against the live image; no missing private media, telemetry or worker code.
6. Confirm encrypted live database backup, immutable rollback image,
   compatible schema rollback plan, and coordinated frontend/backend rollout.
7. Run browser E2E for exactly matching TTN, multiple orders in a conversation,
   unmatched TTNs, idempotent manager confirmation and read-only analyst access.
8. Obtain owner review before merging/deploying or attempting a history backfill.

## Deployment policy

**Draft parity PR only.** Do not deploy this branch, merge PR #327, run
migration 046 on production, execute historical bulk apply or send Meta / Nova
Poshta messages until release gates are passed. CI green is insufficient
without live-image lineage and data-integrity evidence.

Tracked follow-ups: #264 (source parity) and #326 (TTN history reconciliation).

## Disposable migration canary result (2026-10-24)

- Synthetic PostgreSQL **17-alpine** on an internal-only Docker network,
  with no host ports, no live database credentials and no production volumes.
- Upgraded the complete repository migration chain to revision
  `202610230045`, then applied PR #327 migration to
  `202610240046 (head)`: **PASS**.
- Confirmed `direct_order_shipment_links` has 12 columns, RLS enabled,
  and the workspace/conversation/shipment uniqueness constraint.
- The disposable database and Docker network were removed on exit.
- This is a schema-only canary; it does **not** substitute for a populated
  production-like backup restore and authenticated end-to-end test.
