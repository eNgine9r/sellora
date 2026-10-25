# Direct → Nova Poshta TTN → historical order reconciliation

## Verified source baseline (Your Jewelry, 24 October 2026)

Read-only, tenant-scoped, aggregate evidence established:
- 598 conversations have exact tracking-number matches in 607 existing shipments and orders.
- 589 conversations have one verified order and 9 have multiple verified orders.
- 254 conversations include some TTNs absent from CRM shipments; 11 also have a matched TTN, leaving 243 with only unmatched TTNs.
- 0 `direct_conversations.linked_order_id` values were populated before this feature. This **does not mean no sales occurred**.
- These counts are a snapshot, not permanent expected values; redo dry-run before a backfill.

## What the evidence proves

`EXACT_SHIPMENT_TTN` links an outbound, non-synthetic Direct message containing a standalone 14-digit number beginning with `20` to the exact number on an active Nova Poshta shipment in the same workspace, then to the shipment's existing order. Conflicting customers and non-unique shipment matches are **not confirmed automatically**.

It proves correspondence to a CRM shipment/order; it does **not** independently prove provider delivery, payment settlement, products sold, profit, or advertising attribution. Stored historical order/payment statuses remain unchanged.

Missing TTNs are labelled `SHIPMENT_NOT_IN_CRM` and require review, not a false `no sale` claim. The API returns only masked TTNs (first two and last four digits). Raw Direct text does not appear in the response or audit log.

## Data model

Migration `202610240046` adds `direct_order_shipment_links`:
- `workspace_id, conversation_id, order_id, shipment_id, source_message_id, evidence_type`, audit actor and timestamps.
- Unique by `workspace_id, conversation_id, shipment_id`, supporting idempotency and 1:N orders per conversation.
- Workspace-scoped checks in the service, RLS enabled, and Supabase `anon` / `authenticated` permissions revoked.
- `linked_order_id` legacy field is filled **only when exactly one order** can be verified. Multiple orders stay in the link table.
- No customer, order, shipment, stock, profit, delivery, Meta campaign, or payment record is created or modified.

## API and UI

- `GET /api/v1/direct/conversations/{id}/order-evidence`: `ANALYST+`, masked read-only verified and review candidates; explicitly reports truncated scans.
- `POST /api/v1/direct/conversations/{id}/order-evidence/confirm`: `MANAGER+`; the client must provide an exact set of order IDs freshly derived from evidence; one scoped transactional action creates/restores links and sanitized audit entries, or returns `409`.
- The Direct thread displays each proven shipment and existing order, with a distinct warning for unmatched/ambiguous TTNs. Confirmation requires an explicit user action and a second confirmation prompt. When prior orders are proven, a deliberate additional purchase remains possible and is explicitly labelled **Create a new order** rather than mistaken for the original sale.
- Neither endpoint sends an Instagram message, calls Nova Poshta, or triggers a financial or inventory side effect.

## Controlled historical backfill

`backend/scripts/direct_ttn_backfill.py` is **dry-run by default**, returns aggregate counts only and forbids unsafe output. It requires schema 046. Example after migration in a staging environment:

```sh
python -m scripts.direct_ttn_backfill --workspace-id WORKSPACE_UUID
```

For a separate, explicitly approved maintenance window, the operator must review the exact dry-run counters and source parity, verify a recent encrypted and independently recoverable backup, supply the real actor UUID, and set the one-run allow flag plus expected counters. The command uses a bounded lock timeout and remains idempotent.

```sh
SELLORA_ALLOW_TTN_BULK_APPLY=EXPLICITLY_APPROVED \
python -m scripts.direct_ttn_backfill \
  --workspace-id WORKSPACE_UUID --actor-id APPROVED_MANAGER_UUID \
  --apply --expected-conversations REVIEWED_COUNT \
  --expected-links REVIEWED_LINK_COUNT
```

This is an **operator runbook, not permission to run on live data**. Do not execute a bulk mutation until source/runtime parity (#264), migration canary, RBAC and tenant tests, approval and backup are verified. A mismatching candidate count or truncated evidence aborts the write transaction.

## Reproducible disposable PostgreSQL canary (tested)

Run migrations 001→046 on a **fresh isolated PostgreSQL 16** container with no access to production. Then, inside an isolated backend container with the disposable `DATABASE_URL` and workspace-only synthetic data, run:

```sh
SELLORA_TTN_DISPOSABLE_CANARY=YES python scripts/verify_direct_ttn_postgres_canary.py
```

The script refuses to run without the explicit opt-in, checks revision 046 and refuses any database that already contains a workspace. The isolated execution verified exact TTN matching, two orders in one Direct conversation, idempotent retries, cross-tenant denial, source-message provenance, persisted audit entries and single-order legacy compatibility. The disposable database was deleted after verification. It **must never be pointed at the live Raspberry database**.

## Release gate

As of 24 October 2026, a SHA-256 manifest comparison found **58 Python-file differences** between the live Raspberry backend and this PR branch (including 14 live-only modules and four expected new feature modules). Live Raspberry includes event-loop monitoring, media cache, Nova Poshta services and background-worker fixes absent from GitHub `main`. Deploying this branch as a full backend image **could regress live security/operations**. First reconcile live modules (#264, #266) and test immutable ARM64 image with current PostgreSQL revision 045→046, all migrations, and liveness/readiness checks. Frontend release must be coordinated with backend release to avoid temporary API errors.

## Acceptance

- Exact TTNs, repeated messages and replayed webhooks never double-create links.
- All reads and writes filtered by workspace; mismatching customer/order rejects before write.
- One-to-many history preserved; `linked_order_id` only set for single-order dialogs.
- Unmatched TTNs remain reviewable, never silently counted as unpaid or unsold.
- Confirm and backfill work only after expected evidence counts, role authorization and audit.
- No raw messages, full TTNs, secrets or customer PII in logs / telemetry.
- Explicit rollback and recovery evidence before user-facing deployment.