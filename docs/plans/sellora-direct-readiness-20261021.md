# Sellora — Instagram Direct readiness (21 Oct 2026)

## Goal

Existing Instagram Business connection → genuine inbound Direct event → correctly
scoped conversation → qualified lead/prospect (on fresh purchase intent) →
manager-verified order draft/product selection → shipment. Never send autonomous
customer messages, create fake users/orders, or reclassify old history as today's
pipeline without a separate owner review.

## Non-secret runtime audit (Your Jewelry)

- Existing Instagram Business link: CONNECTED, token present and not expired.
- Webhook subscriptions include: messages, postbacks, seen, reactions.
- Webhook worker RUNNING and processing allowed.
- Three stored webhook events processed.
- Four Direct conversations; 21 Instagram inbound and 16 outbound messages.
- Two historical (July) messages meet the deterministic order-intent regex.
- No conversations linked to lead/customer/order yet; historically imported
  conversations are NOT today's fresh sales opportunities.
- Read and customer/lead creation are already present for fresh inbound purchase
  messages, but require a normal new inbound event to exercise the complete flow.
- Meta outbound send/auto-send/AI auto-analysis stay disabled by release policy.

## Fix in this change

1. Split signed multi-entry/multi-item webhook batches into individually
   persistable units, each resolved to the *own* connected workspace. Invalid
   structure fails the whole ingestion before partial writes.
2. Deduplicate provider messages by message event ID *and* hashed business account
   identifier; preserve replay lookup for valid legacy events.
3. Discard unmatched or foreign-account entries and reject foreign sender/
   recipient mappings. Never infer an outbound echo from the first envelope
   entry or an untrusted is_echo flag.
4. Isolate prospect association failures in a transaction savepoint, keeping
   the verified inbound message durable after recoverable automation errors.
5. Add multi-account and replay regression tests.

## Explicit guardrails and follow-ups

- No automatic lead backfill for July historical inquiries. Existing Direct UI
  allows manager-initiated creation of lead/prospect and manual review.
- No live Meta outbound send, ad account mutations, or test purchases in this
  sprint. Real customer-facing actions require owner-operated or separately
  approved validation.
- After this deployment, validate **on the next naturally received genuine
  inbound purchase request**, with consent, that conversation, linked customer,
  lead, catalog proposal, and order draft are consistent in the same workspace.
- Do not count created prospects as paid customers or July messages as new sales.
- Preserve delivery timer, Nova Poshta Payment Control, and prior release for
  rollback. Leave stacked PR in Draft pending Render auto-deploy retirement.
