# Sellora — Instagram Direct → Lead linking (Issue #263)

**Date:** 2026-10-20
**Branch:** codex/2026-10-20-direct-lead-link
**Base PR:** #262 (stacked on #237, #236, #235)
**Release:** Draft only; do not deploy before current live migration/security lineage is reconciled.

## Product decision

An Instagram Direct conversation is an inbound sales channel, but **not every
message is a lead**. A lead is one sales opportunity for a participant within
one workspace and one Instagram connection. Existing Customer prospects are
the identity/profile records; a Lead and Customer may both reference the same
conversation without representing two distinct people or two orders.

- A **new real inbound text message** with explicit deterministic purchase
  intent (existing `detect_direct_order_intent`) creates/links a Lead with
  status `NEW`. This is not an order and does not infer a completed purchase.
- For an ambiguous inbound inquiry, an OWNER or MANAGER can explicitly choose
  **Створити лід** from the Direct dialog. The API requires at least one
  non-synthetic Instagram inbound message already saved in this conversation.
- Synthetic dialogs, echoes, empty/non-sales content, read receipts, reactions,
  edits, and unsupported attachments never automatically create leads.
- History sync applies the same qualification to newly imported inbound text.
  Existing imported messages do not automatically replay or mass backfill.
- Existing `DirectCustomerAutomationService` remains responsible for
  creating or finding the Customer prospect when an order-intent message is
  received. This PR does not enable AI, sending, payment, purchase events,
  new orders, or shipments.

## Backend contract

`POST /api/v1/direct/conversations/{conversation_id}/lead/ensure`

- **Permissions:** MANAGER/OWNER; workspace-header RBAC enforced by existing
  dependencies, including `workspace_id` scoping.
- **Result:** `DirectConversationResponse`, including `linked_lead_id`.
- **Idempotency:** repeated manager clicks or webhook/history deliveries link
  the existing Lead. A PostgreSQL transaction-level advisory lock is derived
  from workspace, connection, and scoped participant identity, and the
  conversation is loaded with a row lock/refresh before mutation.
- **Status:** a soft-deleted or LOST lead is not automatically reused as a new
  sales opportunity. Existing active leads for the same scoped participant
  and Instagram connection in the same workspace are reused.
- **Error codes:** `DIRECT_CONVERSATION_NOT_FOUND` (404),
  `DIRECT_LEAD_INBOUND_REQUIRED` (409),
  `DIRECT_LEAD_INSTAGRAM_REQUIRED` (409).
- **Audit:** `DIRECT_LEAD_CREATE` records entity ID and source metadata,
  no customer message text is copied to Lead notes or audit.
- **Failsafe:** webhook and history-sync lead automation executes within a
  DB savepoint, so a failed lead creation does not discard the verified inbound
  Direct message. History sync records `DIRECT_LEAD_FAILED_SAFE` to retry
  manually.

## Frontend

- Direct customer/order card displays whether a linked Lead exists.
- Unlinked Instagram conversations expose a manager action to create one.
- Linked conversations offer navigation to the Leads list.
- Ukrainian and English strings are updated; backend enum values unchanged.
- Existing prospect/order creation flows and safety controls remain in place.

## Validation

- Focused unit / integration-style tests for lead lifecycle, replay,
  workspace isolation, sibling thread identity, synthetic dialog exclusion,
  manual explicit action, message processing and history sync.
- Security route inventory updated for 1 additional protected POST.
- TypeScript typecheck + ESLint modified frontend: PASS.
- Direct AppShell static regression 18 checks: PASS.
- Meta Instagram regression 23 checks: PASS.
- Full GitHub CI on this draft PR is the authoritative release gate.
- No production database mutation, no provider message send, no live
  customer E2E test from this development branch.

## Remaining E2E gate (requires approved real test account)

From the authorized Instagram test account, send a genuine purchase inquiry
and then a second message. Verify *in the target workspace only*:

1. Signed provider event arrives; one conversation and inbound message stored.
2. Exactly one linked Lead appears; duplicate delivery does not create another.
3. Existing Customer prospect is matched/created without duplicated identity.
4. Manager selects product and confirms an order; do not auto-create order.
5. Verify TTN draft / shipping preparation separately; avoid real shipment
   or customer send without explicit owner approval.

## Release blocker

The active Raspberry backend packages Alembic `202610200038`, while the PR
stack source packages only through `202607220036`. Do not deploy a full
checkout image from this branch, since it can drop later security changes
even when CI passes. Reconcile runtime source before release.
