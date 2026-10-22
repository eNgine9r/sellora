# Sellora — Historical Instagram Direct ↔ Nova Poshta reconciliation

**Workspace:** Your Jewelry  
**Execution date:** 2026-10-22  
**Source of truth:** existing workspace-scoped Instagram Direct messages and read-only Nova Poshta InternetDocument.getDocumentList responses.

## Scope and limitations

- Instagram import was `PARTIAL`: 2,000 Meta conversations scanned; 1,729 provider access errors. Missing content is not reconstructed or invented.
- Nova Poshta archival pagination MUST use the `info.totalCount` and numbered `Page` property. Provider may return only 100 documents on page 1 even with `GetFullList=1`.
- Retrieved the complete May–October 22, 2026 monthly windows: **795 distinct waybill numbers** (144 + 134 + 154 + 168 + 127 + 68).
- Previous **484** individually historical spreadsheet-backed finance orders are dated January–April 2026 (plus two in March 2025), therefore the new importer is explicitly restricted to May–October 2026.
- Create new orders only on (1) uniquely matching provider waybill number in one Instagram thread **and** (2) exact normalized recipient phone written in an **INBOUND** message of that same thread. Reject conflicting phones, inconsistent names, ambiguous existing customers, relabeled duplicates on the same day, missing recipient/location and cross-tenant records.
- Never infer product SKU, selling price, realized revenue, delivery confirmation or payment confirmation from an NP shipping-label record.
- Order is explicitly `is_historical=True`, `status=CONFIRMED`, `payment_status=PENDING`, monetary totals all zero, quantity 1 of *Інше (товар не визначено)*, no stock transaction. Requested COD (if present) stays on Shipment.cod_amount, **not Order.revenue**.
- Customer name is the recipient-contact name provided by Nova Poshta. `customer.source_direct_conversation_id` ties to a unique matched conversation. Region is not guessed where the API provides only an opaque code; city, location and warehouse are retained.
- Idempotent: `NP-<tracking number>` order number, existing shipment tracking and conflict checks; foreign keys, auditable system reconciliation actions. Never update 484 preexisting historical finance orders.
- Incomplete or conflicting source evidence is a review exception, not an automatic sale or customer identity. Receiver may not always be the purchaser.
- Raw provider addresses, recipient phone numbers, customer names, secret tokens and the full archive must **not** appear in CI logs, GitHub comments or public analytics.

## Proven first pass

| 2026 period | Provider archive | Reconstructed orders with two independent confirmations |
|---|---:|---:|
| May | 144 | 104 |
| June | 134 | 98 |
| July | 154 | 120 |
| August | 168 | 126 |
| September | 127 | 99 |
| October 1–22 | 68 | 50 |
| **Total** | **795** | **597** |

Subsequent parsing of spaced/hyphenated Ukrainian phone numbers safely recovered another **10 May records**, for **607 reconstructed orders**. Final workspace-verified totals after all committed writes: **607 customers, 600 addresses, 1,098 orders, 608 shipments and 1,113 order items**. Exactly **607** orders carry the immutable `NP-<TTN>` importer prefix, all with zero revenue/net profit, payment PENDING, and audit provenance. Provider TТН duplicates: zero. Additional months require an authorized bounded second pass; attempts were blocked by Nova Poshta's provider rate restriction, so no claim of complete second-pass coverage is made.

## Validation and operations

- Encrypted full database snapshot made before write and off-host Google Drive upload verified.
- Fresh post-recovery encrypted snapshot `sellora-db-20261022-041400.pgdump.enc` was uploaded and its ciphertext verified in Google Drive after an initial provider quota failure.
- May full execution passed an actual transaction `flush()` of 104 candidate orders/customers/addresses/shipments and was explicitly rolled back before the first commit.
- Each month committed atomically, and DB count/profit/duplicate guards verified after release.
- No new registered Sellora users, changes to OAuth credentials, new payment confirmation, outbound Meta messages or Nova Poshta label creation.
- Stop on provider error or pagination shortfall; do not import a partial month. Requesting many previous years may be disallowed by connected account access and request quotas.
- Before further replay, check fresh off-host backup, rate limits, and use read-only preview. No confirmation, import of a waybill, or lack of it is proof of an actual sale, receipt or payment.

## Remaining work

- Recheck the months that were provider rate-limited after formatted-phone parsing, with paced requests and read-only preview first.
- Review every remaining unmatched waybill separately, prioritize one-to-one waybill/thread links whose inbound recipient phone was absent.
- Connect approved historical orders to a verified product only once catalog evidence exists; unknown item is intentional.
- Verify actual Nova Poshta tracking status separately before changing shipment/order delivery statuses or financial totals.
- Do not automatically merge recipient and Instagram buyer when they might be different people.
