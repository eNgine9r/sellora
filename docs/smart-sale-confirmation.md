# Sellora Smart Sale Confirmation — Nova Poshta TTN + Direct → reviewed sale

## Why

Your Jewelry sells in Instagram Direct, receives payment into mono FOP outside Sellora and creates an external Nova Poshta TTN. The owner wants **a notification and one click after the sale** instead of creating CRM customers, orders and shipments manually.

**Non-negotiables:** no outgoing Direct messages; no monobank token, bank API, refunds or bank-origin attestation; external TTN alone is not proof of itemized purchase, sale price, or bank receipt.

## Implemented flow

1. The already existing NP external TTN collector stores sender-owned documents with dedup by tenant and tracking number. Existing outgoing Direct message with the **exact tracking number** identifies one conversation; ambiguous/missing conversation yields `NEEDS_INFO`.
2. `GET /api/v1/integrations/nova-poshta/external-documents/sale-candidates` (MANAGER+) returns a safe, tenant-scoped queue. Existing direct catalog proposal reuses **literal inbound SKU** evidence (not AI-only suggestions). Exactly one unambiguous active SKU with available stock and catalog price yields `READY_FOR_REVIEW`. Prices are *catalog suggestions*, not inferred negotiated customer prices.
3. In **Shipments → External Nova Poshta TTNs**, owner/manager sees the customer Instagram identity, suggested item, quantity, editable proposed price, and a **Yes, sold** button. Header notification badge shows uniquely matched TTNs needing manager review (desktop and mobile), refreshed at 60s while app is open. Other documents with a uniquely matched conversation show **Needs review** and a **fast manual catalog picker** (product variant, quantity, agreed price) in the same card; manager does not have to open a separate new-order form. Ambiguous or missing Direct conversations cannot be confirmed until correctly linked.
4. The one-click button explicitly means: “I verified the customer's receipt in Direct, the actual funds arrival in my own bank app, and the itemized sale details.” These are human assertions; backend does not contact the bank.
5. `POST /api/v1/integrations/nova-poshta/external-documents/{document_id}/confirm-sale` (MANAGER+) rechecks the TTN and the same conversation, reacquires the catalog evidence and inventory checks, resolves or creates a **single Instagram customer**, creates a `CONFIRMED`, `PAID` (human-attested) CRM order, and links the *existing* NP TTN as a `CREATED` shipment.
6. A single PostgreSQL transaction commits: customer, order, inventory **reservation only**, shipment, external TTN link, Direct evidence link, lifecycle change, and audit with actor/time and `HUMAN_ATTESTATION_NOT_BANK_API`. No new external NP document is created; no second charge/sale. Subsequent carrier tracking can transition shipment to in-transit and stock out according to existing rules.
7. The external TTN row is locked on confirmation and moved `UNMATCHED → LINKED` with `matched_shipment_id`. Repeat clicks only return existing sale if tracking, conversation, line item, price and `PAID` status still match; other replays/conflicts receive 409.
8. Long-running Direct conversations can have **multiple sales with distinct TTNs**; their individual `DirectOrderShipmentLink` rows preserve that history without duplicate customer creation.

## Limitations for the current MVP

- No actual bank lookup; no guarantee that funds arrived. Approval records the staff's assertion, and is **not a separate provider-verified bank transaction ID**. The exact transaction ID is not known from the TTN.
- The NP external list initially stores TTN, status, provider document reference, **not recipient phone, recipient full name or branch**. The automatic CRM customer has only the confirmed Instagram identity and any existing known CRM details. These fields are not fabricated.
- A product appearing in a message may be just a question, not the final purchased item. The manager must **review the visible item and price** before confirming. If the catalog has no unambiguous explicit SKU, the fast picker requires one manual product selection before the confirmation click. For multi-item baskets use standard order creation.
- The final **agreed price** may differ from the catalog: edit the suggested amount before confirming. Where there is no reliable SKU in the chat (observed in Your Jewelry), manager can explicitly select a real catalog variant, quantity and price; the backend enforces workspace, active variant and stock. This is still a human-reviewed sale, never an AI-invented item.
- Only one distinct line item is supported for one-click MVP. Multi-SKU baskets, missing inventory, ambiguous identities, returns/discounts and provider conflicts are **NEEDS_INFO** and never create a phantom sale.
- Real-time push notifications when Sellora isn't open are **not** part of this iteration. Existing in-app bell badge and 60s polling are the first implementation.
- Reservation does not mean actual stock-out. TTN status `CREATED` does not imply the parcel was physically handed to the carrier. Existing tracking workers handle subsequent state transitions.
- No custom schema migrations: uses existing `nova_poshta_external_documents.matched_shipment_id`, `direct_order_shipment_links`, `orders`, `shipments`, `customers`, and `audit_logs`. No bank connection is required.

## Security / QA gates

- Every select is restricted by `workspace_id`. Management endpoints require MANAGER+.
- Candidate evidence never includes full recipient contact or bank transaction data. TTN is masked on the new API and notification.
- All decisions rechecked with a row lock. No evidence → no auto-sale; partial or duplicate → reject and rollback.
- No AI generation or outgoing message at confirmation time; only saved Direct analysis and exact SKU scanning.
- Confirming returns a created sale ID, not a payment from bank. Price is explicit manager-reviewed input; unknown COGS remains unconfirmed so profit is not fabricated.
- API replays cannot double-reserve inventory or double-count sales; different details on an already linked TTN return conflict.
- Manual review order fallback remains available.

## Update: bounded evidence-based price hints (12.11.2026)

A provider-free **read-only** extension finds recent explicit monetary quotes
made by the shop in Direct **before the exact TTN**. It ignores inbound amounts,
bare numeric strings, prices quoted with delivery/fee/deposit context, synthetic
messages, and anything older than seven days or separated by a previous TTN.
Evidence uses source `direct_message.id`, workspace scope, and no raw message
text in the API response. Two or more distinct prices show selectable options:
Sellora never silently decides which one was finally accepted. A single recent
quote can prefill the per-item amount, but the manager still needs to inspect
and confirm the exact negotiated final unit price.

`SmartSaleCandidate.price_hints` is a list of at most four
`{unit_price, message_id}` tuples. A matching catalog price moves a variant
upward in the chooser, **never** selects it or changes inventory automatically.

The existing `INBOUND_SKU` product suggestion now also requires that SKU's
source message to be inside the same bounded TTN window. A SKU from an older
sale in a reused Instagram conversation cannot preselect the new sale.

**Live read-only calibration:** 17 TTN candidates, 12 with at least one
non-conflicting seller-price message within the bounded window; 10 have a
single distinct quote and 2 have several; no product variant can be established
from exact SKU/title evidence. These numbers are dynamic and **do not**
mean 12 verified sales or 12 negotiated prices. Product photo/link-to-catalog
mapping and evidence-backed multi-line order extraction still require later
development. The existing manual product picker is intentionally preserved.

No new database tables/migrations, no banking API, no messaging to Instagram,
no release test that modifies customer sales.
