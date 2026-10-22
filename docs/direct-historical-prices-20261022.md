# Direct historical prices — provenance-safe recovery

Date: 2026-10-22. Workspace: Your Jewelry.

## Starting point

- 607 reconstructed NP-related historical orders.
- 384 with requested COD amounts, 57 with declared parcel values, 166 without an amount.
- Existing financial revenue and net profit must not be altered. Parcel insured value and COD collection request are not proof of income.
- Import uses the original customer-to-Instagram conversation evidence; no customer/accounts/shipment creation.

## Matching method

- Scan ALL 166 remaining unpriced NP orders and their corresponding Direct conversation history within the order’s creation date −5 days through +2 days.
- Extract currency-tagged amounts, explicit seller-written final total (`разом`, `всього`, `до оплати`, `загалом` etc.), and supporting messages.
- For automatic total acceptance: exactly one qualifying seller final-total assertion, sum of item amounts equals the final total, **the exact imported TТН appears in a later outgoing Direct message**, no cancellation, and no sibling order in same thread within ±5 days.
- `DIRECT_CONFIRMED_TOTAL`: additional explicit affirmative follow-up from the buyer in the 3 days after the seller summary. This confirms agreement language, **not actual payment**.
- `DIRECT_ESTIMATED_TOTAL`: all other strong evidence is present, but buyer confirmation is unavailable. This remains an estimate and should not be counted as received revenue.
- `REVIEW_REQUIRED`: more than one total, insufficient support, multiple independent amounts, or competing order contexts. Retain up to 50 closest candidate messages with their **message IDs**, timestamps, extracted numeric amounts and flags, plus full message candidate count. No raw message text is copied into order evidence.
- `NO_PRICE_MENTIONS`: no readable relevant numeric prices. A missing message is not reconstructed.
- Preserve order `revenue=0`, `net_profit=0`, `payment_status=PENDING`. No item SKU assignment, inventory mutation or outgoing Instagram message.

## Dry run 2026-10-22

| Outcome | Orders | Amount, UAH |
|---|---:|---:|
| High-confidence message total + buyer reply + TTN | 3 | 2,643 |
| Seller arithmetic total + TTN; buyer reply unavailable | 11 | 8,606 |
| Needs source review | 136 | Not booked |
| No price mentions | 16 | Not booked |
| **All** | **166** | **11,249 in estimated historical order values** |

The two totals are not added to accounting revenue or net profit. Historical estimate source is displayed explicitly in frontend, and users may open the actual price message from order details. Deep links include `conversation` and `message` query parameters, and the existing Direct UI highlights/scrolls to an available message.

## Safety and deployment

- Migration `202610220042`: nullable `orders.historical_value_evidence` JSONB with only structured proof; no customer text.
- `backend/scripts/recover_direct_historical_amounts.py` is an explicit, idempotent maintenance tool that defaults to read-only preview; `--execute` requires successful migration and fresh backup.
- Every applied amount records an order audit event with the selected message ID, matching conversation, TTN verification and arithmetic flag.
- No protected provider tokens, raw customer chat history, private phone numbers or name information are logged or committed.
- Full baseline remains 441 previously valued plus 166 unknown; after successful guarded execution it should become **455 valued and 152 still without an amount**, subject to last-minute data changes.
