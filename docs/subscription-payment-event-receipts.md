# S8.2a — Internal payment event receipts

`SubscriptionPaymentEventService.record(workspace_id, event)` stores normalized
provider event evidence. It has no public API, checkout, real PSP calls, signature
verification, feature gating or subscription/workspace mutations. A receipt does not
establish payment success or authorize a subscription term.

## Trust boundary

A future PSP adapter must verify the provider signature against the original request,
authenticate the merchant account and bind that account and transaction to the intended
workspace **before** invoking this internal service. The caller supplies a trusted
workspace UUID. This service does not authenticate a webhook or check user membership;
there is no callback endpoint in this package. Do not pass unverified request data to it.

The typed input whitelists provider, provider account reference, external event ID,
transaction reference, event type, exact amount, currency and occurrence time. The
adapter must supply opaque, non-PII references. No raw payloads, tokens, card details,
customer names, emails, addresses, descriptions or arbitrary metadata are accepted or
stored. String validation rejects whitespace, email/URL syntax and non-ASCII input;
it cannot establish that a provider's opaque identifier contains no personal data.

## Replay and transaction contract

- `(provider, provider_account_id, external_event_id)` identifies one receipt globally.
  An account namespace is mandatory; event IDs are not assumed unique across merchants
  or providers. References are case-sensitive; provider codes use lowercase tokens.
- Canonical fingerprint v1 is SHA-256 over the explicit whitelisted fields, the workspace
  UUID and format version. Field order is stable; amounts use six decimal places and
  occurrence times use UTC with microseconds. Equivalent decimal scales and timezone
  offsets therefore replay the original receipt.
- The first receipt wins. PostgreSQL `ON CONFLICT DO NOTHING` handles competing inserts;
  the subsequent lookup always includes `workspace_id`. Exact replay returns the same
  receipt ID and reception time. Changed transaction data or a different workspace for
  the same provider identity raises the same generic conflict, without returning the
  original workspace or its receipt. No original evidence is updated.
- Money must be a finite, nonnegative `Decimal`, strictly below `100000000000000`, with
  at most six nonzero fractional decimal places (`NUMERIC(20,6)`). Floats and lossy
  rounding are rejected. Three uppercase ASCII currency letters are required. These
  are storage constraints, not approved pricing or currency-specific exponent rules.
  Zero amounts and arbitrary event types carry no entitlement meaning.
- `occurred_at` must be timezone-aware and is normalized to UTC. `received_at` is
  assigned by the database, separately from provider occurrence time.
- The caller owns commit/rollback. At PostgreSQL's default READ COMMITTED isolation a
  competing insert waits for the first transaction: its commit yields replay/conflict,
  and its rollback permits insertion. Higher isolation may require retrying the whole
  transaction after serialization failure. A receipt must not be acknowledged as durable
  before its caller commits.

## Persistence and rollout

Migration `202610290052`, after `202610290051`, adds only
`subscription_payment_event_receipts`. It enables backend-only RLS and revokes grants
from PUBLIC and optional `anon`/`authenticated` roles. No client policies are installed.
As with existing backend-only tables, the backend must use its approved table-owner or
RLS-bypass connection; a separate non-bypass role requires an explicitly reviewed RLS
policy and least-privilege grants, not a bare grant alone.

PostgreSQL triggers reject UPDATE, DELETE and TRUNCATE. The workspace foreign key uses
RESTRICT, so workspace deactivation remains possible but hard deletion cannot destroy
receipt evidence. Administrative DDL remains an explicit operational responsibility.
An empty-table downgrade is allowed; it takes an exclusive lock before checking so a
concurrent insert cannot be silently dropped. A populated ledger blocks downgrade.

Focused unit tests run locally. Real persistence, duplicate, foreign-tenant, immutability
and competing transaction tests use only the existing disposable subscription CI step:
`SELLORA_SUBSCRIPTIONS_DISPOSABLE_CANARY=YES` and the exact database name
`sellora_subscriptions_canary_isolated` are required. Race tests use separate PostgreSQL
connections and verify lock contention; they cannot run under the SQLite unit setup.

No production migration or rollout is authorized by this package. A later billing policy
must apply verified evidence, audit events and term changes atomically and must first
have approved commercial facts, including pricing, quotas, supported currencies, trials,
cancellation/refund rules and merchant account association. This ledger is only evidence.
