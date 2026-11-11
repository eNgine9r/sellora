# Sellora AutoSales — monobank payment evidence (phase 1)

**Implementation:** Issue #395. First owner pilot workspace: Your Jewelry.

## Shipped

- `bank_payment_evidence` workspace-scoped ledger for **IBAN FOP**, **FOP card**, and **mono merchant payment links**, plus unknown account credits and acquiring payouts.
- Deduplication key: `workspace_id/provider/provider_account_id/external_reference`. An IBAN/card label change must never create a second bank event.
- Unified **integer minor-UAH amount** (no floating-point money); currency limited to UAH. No bank or customer PII attached beyond scoped event/account identifiers.
- Safe preview and manual evidence import (MANAGER preview, OWNER import), limited to 200 rows/request, with explicit repeat and ambiguous classification.
- REST `GET /api/v1/finance/bank-evidence?limit=50&offset=0` (MANAGER+) returns latest evidence, `POST /preview` (MANAGER+), `POST /import` (OWNER). Requires normal Sellora workspace session context.
- Frontend Finance > monobank view shows evidence review and **bank integration disconnected**. Ukrainian and English labels.
- Monobank statement and merchant invoice payload normalizers are pure functions only. They are **not connected to an HTTP client**, do not authenticate events and cannot mark an order paid. No live bank credentials used.
- Alembic `202611110053`, tenant-scoped indexes, RLS enabled and `anon/authenticated` table grants revoked. Rollback disallowed when records exist.
- Every manual record has `origin=MANUAL_IMPORT` and a review reason. Candidate order ID is a hint, not an allocation.

## What this deliberately does not do

- Does **not** connect to mono FOP or merchant API, receive webhook callbacks, fetch bank transactions, import real bank data, recognize actual customer receipt images, auto-allocate funds, send customers any messages, or update `orders.payment_status`, `orders.revenue`, `orders.net_profit`, stock or cash metrics.
- Does not mark manually imported evidence provider-verified. Never accept `bank_verified` from request.
- `ACQUIRING_PAYOUT` must not be counted as a second customer payment after a paid merchant invoice. Positive bank statements are classified `UNCLASSIFIED_CREDIT` until reconciled.
- In a later phase, only authorized monobank provider/Open Banking access may supply bank-attested provenance. Merchant invoices require validated signed webhooks and authoritative status re-fetch, including stale/out-of-order event handling.
- The existing Direct -> Order #386 pipeline needs real itemized orders before automatic matching is possible.

## Manual import example (anonymized TEST values only)

```json
{
  "rows": [{
    "provider_account_id": "demo-mono-fop-account",
    "external_reference": "demo-bank-transaction-001",
    "rail": "BANK_IBAN",
    "kind": "CUSTOMER_PAYMENT",
    "amount_minor": 74900,
    "currency": "UAH",
    "occurred_at": "2026-11-11T08:00:00Z",
    "is_hold": false,
    "order_number": "DEMO-0001"
  }]
}
```

The response is always `REVIEW` for phase 1, with `candidate_order_id` populated only after verified tenant-scoped, exact amount/order-reference matching. Do not send authentic bank files, personal banking tokens or customer documents to GitHub.

## Next gated work

1. Authorized bank provider connection for mono FOP account statements with consent, revocation, backfill, rate limits and encrypted credentials.
2. Authorized merchant invoice status read and signed webhook verification; dedup across cash-transfer payouts and invoice payments.
3. Direct receipt provenance and order-specific reconciliation including customer identity and partial payments, an allocation ledger, reasoned staff review queue.
4. Enable payment status transitions only after unique bank-provider-verified settlement + matching receipt and exact existing order; comprehensive integration tests and monitored release.
