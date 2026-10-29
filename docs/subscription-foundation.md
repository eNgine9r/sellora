# S8.1 — Workspace subscription foundation

The current subscription record belongs to a workspace, not to an individual login.
`GET /api/v1/workspaces/current/subscription` is read-only, OWNER-only and selected by
`X-Workspace-ID`. Both the route guard and service verify active membership. Responses
use `Cache-Control: no-store`. There are no public subscription mutations.

## Term contract

- Stored states: `PENDING`, `TRIALING`, `ACTIVE`, `PAST_DUE`, `CANCELED`, `EXPIRED`.
- No record means `UNMANAGED`. No backfill, automatic trial or automatic enrollment
  is performed. `workspaces.subscription_plan` remains unchanged and is not evidence
  of payment.
- Datetimes are timezone-aware and normalized to UTC. A term is `[start, end)`.
- Only `ACTIVE` and `TRIALING` can report `has_current_term=true` within that interval.
  A future term displays `PENDING`; an ended active/trial term displays `EXPIRED`
  without writing to the database.
- `cancel_at_period_end=true` preserves the remaining active/trial term. `CANCELED`
  represents immediate termination. Pending, overdue, canceled and expired states
  never report a current entitlement. No unapproved grace period is invented.
- `enforcement_enabled=false`: this foundation does not change CRM authorization,
  gate integrations, lock existing shops or grant paid feature access.

## Data and rollout

Migration `202610290051` adds one current record per workspace. It enables RLS and
revokes direct public/anon/authenticated access, matching the backend-only data path.
The unique workspace constraint also indexes the tenant lookup. Migration tests run
only in the separately created `sellora_subscriptions_canary_isolated` database.
An empty-table downgrade is supported; a populated table blocks destructive rollback.

Do not migrate production or enable payments as part of this PR. A later release
requires the usual backup, migration gate, pinned image, readiness and rollback
verification; deployments using a non-owner database role also need an explicit
least-privilege backend grant. Existing access and legacy plan labels are preserved.

## Next package

S8.2 requires approved pricing, quotas, currency, trial and cancellation/refund terms,
plus a merchant account. It adds verified and idempotent payment events, checkout,
renewal/cancellation operations and history. A status row is not a payment ledger;
payment evidence and audit events must precede exposed write operations or enforcement.

The authoritative development queue and historical evidence remain in
[Sellora-Development-Plan.md](https://chatgpt.com/library?file_id=libfile_25c9acecc95481919bc4373b85682f57&account_id=personal).
