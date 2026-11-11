# Sellora / monobank security and acceptance gate

**Scope:** authorized monobank FOP account information (IBAN/card), and merchant-acquiring payment-status reconciliation. Customers are never contacted by Sellora.

## Decision: least privilege is mandatory

1. FOP transaction statements: connect through an **authorized provider solution** (monobank provider API / appropriately authorized AISP with merchant consent, and the right FOP account scopes). AISP must not be conflated with PISP. No customer Personal API token collection for multi-tenant SaaS.
2. Merchant acquiring API: monobank's **X-Token** also grants access to write/refund endpoints. A GET-only code path is *not* a read-only bank credential. Owner's account cannot be called safe merely because Sellora only calls GET.
3. Until the bank offers a restricted status-only token or an independently assessed isolated service is in place, merchant API access is **NOT enabled on the production Raspberry Pi**. A compromised unrestricted token could authorize a refund outside Sellora.
4. Credentials are NEVER collected in chat, pushed to git, rendered in the browser, logged, included in backup manifests, or stored unencrypted. Approved credentials should be mounted read-only as dedicated secrets in the isolated worker, with rotation, revocation and bank-side least privilege when supported.
5. Before approval: CSV import in the owner's Finance view is optional and **evidence only**: `MANUAL_IMPORT`. Neither bank nor merchant accounts are connected, and no payment status transitions occur.

## Current implementation

- Read-only merchant client only exposes `GET /api/merchant/statement` and `GET /api/merchant/invoice/status`, pinned to `https://api.monobank.ua`, TLS verification by library default, no redirects, 8 s request timeout, 512 KiB response maximum, bounded statement window.
- Unsigned/manipulated invoice callback cannot pass ECDSA/SHA256 verification of exact **raw** bytes. Bank public key must be fetched/pinned independently; no webhook endpoint is active yet.
- Merchant statement normalizer separates original checkout amount from settlement, rejects non-UAH, non-success, held and cancellation-history records. No implicit order ID from provider `reference`.
- Manual owner upload requires header-driven CSV in Sellora's explicit template; unique provider/account/transaction ID, timezone-aware timestamp, exact decimal-to-minor conversion, max 200 rows and 1MB, server-side RBAC and revalidation, preview and explicit confirmation. No synthetic transaction IDs.
- Existing bank evidence migration `202611110053` includes tenant `workspace_id`, unique key, RLS enabled, no anonymous/direct authenticated table grants. Order/finance revenue and profit not mutated.
- Existing production server: nonprivileged read-only-root container; backend port bound to localhost; protected deployment env (600) and encrypted backups (700). This does **not** substitute for bank-side approval, a pen test, key isolation, or incident response.

## Live connection must remain blocked until all gates

- [ ] Bank authorizes provider / AISP and permitted FOP account scope; manager documents validity, consent and how to revoke.
- [ ] A separate merchant API token with read-only grants is verified **or** a dedicated isolated GET-only bank connector is reviewed, using a token that is still treated as high risk.
- [ ] Read secrets from a proper secret mount (owner-managed, auditable rotation, no shared backend process environment), restrict network egress, no token in request bodies/URLs/logs.
- [ ] Verified merchant invoice-to-order reference (not amount-only matching), secure raw-body webhook signature, authoritative status re-fetch, replay & out-of-order protection.
- [ ] Cash reconciliation ledger deduplicates merchant success from later FOP acquiring payout, supports refunds and partial payments and captures actual bank settlement.
- [ ] Direct customer identity and itemized order #386 verified; receipt image is *supplemental evidence*, not bank confirmation.
- [ ] Run security/tenant integration tests, independent review of bank scopes, staging live-pilot with owner permission, rollback-forward compatible with Alembic.
- [ ] Production on-call monitoring and disconnect/revocation tested. No auto-`PAID` before the whole chain is verified.

## Owner action (when bank access is ready)

Owner authorizes account access **in monobank's official approval flow**, or provides written confirmation of accepted provider authorization. A sanctioned merchant credential must be installed via the protected server secret workflow by the authorized operator — not transmitted through chat. If such limited access cannot be obtained, use review-only CSV flow; do not deploy an unrestricted refund-capable token as though it is read-only.

## Evidence-only CSV template

Open **Finance → monobank → Download CSV template**. Columns:

`provider_account_id,external_reference,rail,kind,amount_uah,occurred_at,is_hold,invoice_id,order_number`

- `rail`: `BANK_IBAN`, `FOP_CARD`, `MONO_ACQUIRING_LINK`, `UNKNOWN_ACCOUNT_TRANSFER`.
- `kind`: `CUSTOMER_PAYMENT`, `UNCLASSIFIED_CREDIT`, `ACQUIRING_PAYOUT`, `REFUND`.
- `amount_uah`: exact positive decimal with up to two decimal digits (e.g. `749.50`); no floating-point money.
- `occurred_at`: UTC or timezone-offset ISO 8601 (e.g. `2026-11-11T08:00:00+02:00`). Unknown exact time must not be fabricated.
- Account ID and external reference are **provider transaction identities**, not account numbers, passwords or card PANs.
- A pending, unmatched, reversed, duplicate or manually uploaded entry **cannot automatically mark the order paid**.

## Test and audit evidence

Targeted tests include fake HTTP transport, no POST/cancel call support, URL and invoice path injection rejection, token non-disclosure on 403/429/timeout, ECDSA tamper/key mismatch, merchant payout and refund guards, CSV malicious numeric payloads, 200-row limit and duplicates. Full GitHub CI is the merge gate.
