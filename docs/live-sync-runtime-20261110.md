# Sellora runtime: inbound Direct leads and Nova Poshta external TTNs (2026-11-10)

Production pilot scope: **Your Jewelry** only, on Raspberry Pi `btc-radar`. Worker sources are in `backend/app/services/direct_inquiry_lead_worker.py` and `backend/app/services/nova_poshta_external_poll_worker.py`.

## Verified deployment
- Database `cznlsqgvwmccwkomjbeu` migrated additively from `202610270049` to `202610280050` after encrypted production backup and a successful **disposable PostgreSQL full restore + migration rehearsal**.
- Live image `sellora-backend:np-inbox-additive-20261110` is an overlay of the prior authenticated live container image, not a wholesale rollback to a repository build. Backend passed health and Instagram webhook worker checks.
- systemd user timers on `btc-radar`: `sellora-direct-lead-sync.timer` (90 seconds), `sellora-np-external-inbox.timer` (15 minutes), `sellora-np-tracking.timer` (15 minutes). Unit files are host-owned, not yet distributed by generic Docker Compose.
- Direct inquiry worker uses existing `DirectLeadService._ensure` with participant lock and workspace-scoped deduplication. Genuine inbound Instagram text may open a **lead**, never an order, payment, shipment or revenue.
- External TTN worker only lists sender's provider documents and stores `LINKED`, `UNMATCHED`, `CONFLICT` inbox evidence. It scans one date per run (typically today, rotating older dates), not seven days in one burst. Host wrapper supplies `flock` lock, rate limit cooldown and last-success marker.
- The tracking worker's candidate scheduling uses the last verification **attempt** (audit ledger), not only `nova_poshta_synced_at`. Unknown carrier code `3` is kept unverified, not delivered.

## Required safety gates and operations
1. Keep exact database/workspace targeting, RBAC, read-only provider API usage and audit records. Never infer a paid or delivered order from a Direct inquiry or bare TTN.
2. Before replacing image: encrypted backup, full disposable restore rehearsal, migration head verification, dry-run, rollback image retained, health and webhook smoke tests.
3. Watch `NP_EXTERNAL_POLL_OK`, `NP_TRACKING_SUMMARY`, `DIRECT_LEAD_SYNC_SUMMARY`, server health, DB `alembic_version`, last webhook, and last new lead/confirmed order times.
4. Provider `Too many requests` should activate at least one-hour cooldown for external scanning, with no unbounded retries. Old TTNs with `StatusCode=3` require review; never mark them delivered.
5. Open orders only when authoritative customer/product/quantity/price confirmation exists. Missing confirmed order source from Horoshop/Direct remains a separate P0 gap; invoice/payment recognition must remain explicit.
6. Date-sensitive lead KPIs need separation between `created_at` (CRM ingestion date) and `first_contact_at` (customer's source event). Backfilled leads are not new customer contacts today.
7. Remaining multi-workspace SaaS rollout must parameterize exact workspace selection and verify tenant isolation before enabling beyond Your Jewelry.

## Verification queries (read only)
```sql
SELECT version_num FROM alembic_version;
SELECT match_state, count(*) FROM nova_poshta_external_documents GROUP BY 1;
SELECT count(*), max(first_contact_at) FROM leads WHERE deleted_at IS NULL;
SELECT count(*), max(nova_poshta_synced_at) FROM shipments WHERE deleted_at IS NULL;
```
