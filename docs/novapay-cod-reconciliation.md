# NovaPay / FOP bank COD reconciliation — staging MVP

## Business decision

Your Jewelry receives Nova Poshta cash-on-delivery payouts into a FOP
business account through NovaPay or a bank. Sellora needs to display **actual
COD receipts** next to **unverified archive amounts**, separately from normal
order sales revenue.

Official Nova Poshta COD agreements provide payment registers including TTN,
payment date, amount and fees. NovaPay business banking provides statements.
This MVP does NOT access the account, store bank login details or claim to
have connected an undocumented NovaPay API.

A TTN label, declared parcel value, delivery status, a customer's Direct
message, or a requested COD amount is NOT proof of a bank deposit.

## API / audit / tenant isolation

- GET /api/v1/finance/cod-reconciliation — analyst+,
  optional `date_from`/`date_to` for imported receipts (based on actual paid
  date). Unverified historical sums are always lifetime/archive totals.
- POST /api/v1/finance/cod-reconciliation/preview — manager+; read-only,
  max 300 normalized payment rows.
- POST /api/v1/finance/cod-reconciliation/import — manager+; explicit action
  after preview and acknowledgement, rechecks inside a workspace row lock;
  source reference uniqueness, matching only exact 14-digit TTN + amount
  against a scoped active Nova Poshta shipment; audit per inserted entry.

`NOVAPAY_REGISTER` and `BANK_STATEMENT` are English source enums.
`MATCHED` means unique TTN / COD evidence match; it is **not**
the full order's paid status. Conflicts or missing details are `REVIEW`.
Repeated source+reference are `DUPLICATE` and skipped; second receipt for
the same TTN is review-only even if from another payment source. Bank
statements without TTN are review-only, not guessed by amount.

New `cod_payment_evidence` table stores separate immutable financial
evidence, not order cost, revenue or inventory. RLS enabled, anon and
authenticated direct-table grants revoked; only the protected backend API
should query it. Migration is revision 202610230044, dependent on 043.

**No** automatic update to `orders.revenue`, `payment_status`,
`product_cost`, `net_profit`, confirmed historical snapshots or stock.
No new accounting entries are generated. A future separate acceptance gate
may post matched payments to a proper order-payment ledger, including
partial prepayments, fees and refunds; it needs verified full-sale-price
evidence and reconciliation.

## File format

In Finances choose NovaPay register or bank statement and upload a
UTF-8 CSV with headers (Ukrainian and English aliases supported):

```csv
tracking_number;gross_amount;fee_amount;paid_at;reference
```

A real register must supply **actual gross payment amount before fees**,
the paid calendar date (YYYY-MM-DD or DD.MM.YYYY), a shipment tracking number
and preferably a unique transaction reference. The date-only importer stores
12:00 UTC for that day and does not imply this was the precise transaction
timestamp. Bank rows lacking a TTN require a unique reference and remain
review-only. Multiple transfers batched into one bank credit cannot safely
be distributed to individual orders without the NovaPay per-TTN register.
Maximum 300 payment rows per import; no credentials or bank account numbers
are required.

## Dashboard

- Sales revenue (existing) retains its period and confirmed-source rules.
- Confirmed COD register receipts (NEW) reflect verified imported payment
  evidence in selected date range; do not add them to the sales KPI.
- Historical amounts needing reconciliation (NEW) are all-time unverified
  order evidence, not received income.

## QA / rollout

- Backend unit tests for exact matches, partial COD, refunds/returns, wrong
  amounts, double count, no TTN, invalid money, idempotency, and invariants.
- TypeScript and ESLint on touched frontend files.
- Backup staging DB; migrate 043 -> 044 BEFORE starting new backend image.
- Deploy backend via a Raspberry-specific overlay preserving startup
  supervisor, revision preflight, arm64 architecture, watchdog health checks,
  and rollback-compatible migration lineage.
- Deploy frontend after backend health and API smoke tests pass.
- All historical 484 confirmed COGS snapshots, 607 unvalued orders, normal
  orders, their recognized revenue, and stock must remain unchanged.
- Historical register import requires a real file supplied by the owner;
  no sample or fabricated transactions must ever be posted.
