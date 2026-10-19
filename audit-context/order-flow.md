# Sellora order-flow context — 2026-10-19

Scope: bounded read-only code audit of Instagram/Direct → customer → catalog/order → Nova Poshta TTN → customer message. No runtime customer state, credentials, provider writes or sends inspected/executed. Evidence reflects existing source on codex/2026-10-19-raspberry-backend before product modernization changes. This record maps contracts and open questions; it is not a vulnerability verdict.

## What is already implemented

| Stage | Implemented behavior | Evidence |
| --- | --- | --- |
| Webhook receipt | HMAC validates raw body; parser bounds payload; event deduplicates, maps Instagram account to a unique active connection/workspace; unmatched event ignored | api/v1/instagram.py L135-L141; integrations/meta_instagram/services/webhook_service.py L27-L85 |
| Inbox processing | Worker consumes verified events, builds/reuses participant thread, deduplicates provider message, handles echo/seen/reaction/edit, sets unread and reply windows | webhook_processor_service.py L11-L37; inbound_message_service.py L47-L167 |
| Prospect/customer | Explicit order-intent text creates/reuses customer by workspace Instagram identity; no phone needed; relationships and audit preserved | direct_customer_automation_service.py L46-L126 |
| Contact/delivery extraction | Last20 text messages → structured AI fields → Nova Poshta directory validation → high-confidence missing fields filled; conflicts require explicit overwrite | direct_customer_data_extraction_service.py L247-L455, L457-L498, L560-L596 |
| Product mentions | Generic AI analysis stores raw product mentions (text/quantity/color/size/SKU), reply draft, intent; no catalog ID selection in this schema | ai/schemas/structured_output.py L18-L54; direct_intelligence_service.py L17-L41 |
| Order + shipment | Three-step wizard reuses customer/default address, manager chooses variants/quantity/price/payment; one idempotent backend service reserves stock and creates shipment draft before TTN call | wizard L94-L143,L211-L276,L304-L371; order_fulfillment_service.py L271-L385,L419-L525 |
| Nova Poshta | Verified sender/connection/environment/workspace permission gate; durable document operation; provider marker reconciliation; ambiguous result blocks blind retry | nova_poshta_service.py L110-L163,L422-L607,L862-L1021 |
| Order lifecycle | Creating TTN sets shipment CREATED; transit/delivery/return later trigger proper order transitions | nova_poshta_service.py L949-L1021; shipment_service.py L196-L217 |
| Instagram text send | Manager confirmation, reply window, account/token readiness, rate limits, operation idempotency, reconciliation state | api/v1/direct.py L259-L324; outbound_message_service.py L26-L113 |

All backend paths above are relative to backend/app unless frontend path stated. See per-function records:
- functions/order-ensure-candidate.md
- functions/order-apply-customer-extraction.md
- functions/order-fulfillment-create.md
- functions/order-ttn-create.md
- functions/order-direct-send.md

## Cross-function invariants

1. Workspace/customer/variant identity remains server-checked: Direct repositories filter workspace and soft deletion (ai_direct_repository.py L22-L56,L105-L116); customer repository scopes identity matches (customer_repository.py L23-L41); OrderService validates customer/variant workspace/deletion/active state (order_service.py L298-L314).
2. An order is saved separately from provider success. TTN failure must not imply creating a second order (order_fulfillment_service.py L300-L385).
3. TTN creation is distinct from physical dispatch, delivery, payment and profit realization (nova_poshta_service.py L972; shipment_service.py L196-L217; profit_calculation_service.py L52-L83).
4. Cost is an item snapshot supplied by caller, not fetched from a catalog purchase-cost field: order schema L10-L14; order_service.py L106-L129; Product and ProductVariant currently contain no purchase cost.
5. Provider ambiguity must flow through reconciliation state, not blind retry; preserve existing durable operation model (nova_poshta_service.py L506-L517,L534-L607,L897-L947).
6. Message API may respond with a failure/pending/reconciliation operation and HTTP success. UI must inspect operation.status before treating as delivered (direct.py L315-L324).

## Product seams and duplicated responsibility

- Webhook creates prospect on order intent; Direct UI also has a selected-thread/live-intent fallback ensure (page.tsx L195-L203). Both share ensure_candidate rather than different business creation code.
- Generic “AI Intelligence” reply analysis and separate “AI розпізнавання даних” contact extraction are different pipelines. The former stores product_mentions; the latter performs contact autofill. UI presents two analyses with technical English copy and no unified order readiness (direct/page.tsx L697-L698; direct-customer-extraction-panel.tsx L122-L146).
- Copy says AI does not change CRM without confirmation (direct/page.tsx L698), yet extract_now/process explicitly auto-fill high-confidence blank fields (extraction service L105,L294-L302,L380-L428).
- Creating order from Direct navigates to Orders wizard; successful creation invokes a second finalizeDirectCustomerOrder call (wizard L107-L126), so Direct association is not part of the create transaction.
- Wizard result offers copy TTN, return Direct, open Order and open Shipment separately (wizard L289-L297). A TTN-based prepared reply and order shipment status in the Direct card were not found; card exposes a single linked_order_id (direct/page.tsx L638-L655).
- One conversation holds one linked_order_id; card hides create-order after this is set (automation _state L244-L259; page L638-L647). Repeated orders in a long-lived Instagram thread need explicit behavior.
- UI Direct polls conversation/automation at2s and messages1.5s in background (page L70-L96), history3s (L107-L112); extraction polls1.5s active/4s idle in background (extraction panel L78-L87), alongside a live provider. Repositories return entire conversations/messages without pagination (ai_direct_repository.py L22-L32,L105-L116). These are concrete scaling/load boundaries.
- Composer label is “Підтвердити send”, messages expose raw direction, AI panel contains “Instagram connection” / inbound text copy (page L561,L576,L698). Seller-facing vocabulary is inconsistent.
- Composer send uses a new UUID each mutation and clears draft for every successful HTTP response, irrespective of operation.status (page L118-L126). Backend's richer operation state is not surfaced in this callback.

## Financial assumption requiring a product decision

Wizard supplies unit_cost0 for every line (wizard L265); financial preview subtracts only ad/shipping/COD/other costs (L177-L180,L360). Backend faithfully snapshots supplied0 (order_service.py L108-L128) and canonical profit subtracts order.product_cost (profit_calculation_service.py L73-L87). This means a wizard-created order has no COGS unless edited through another cost-aware flow. There is no catalog purchase-cost column in Product/ProductVariant to reuse. Distinguishing unknown cost from genuine0 is also not represented in current OrderItemCreate default (schemas/order.py L10-L14).

## Runtime gates deliberately left open

- Worker enable flag defaults false (runtime_worker.py L35-L36); event processing also has separate settings gate (webhook_processor_service.py L12-L13).
- Customer extraction requires feature flag/API key; actual provider readiness and current deployment flags not inspected here (extraction service L91-L95).
- Nova Poshta live connection/readiness/send validity not tested; read-only readiness endpoint already exists (nova_poshta_service.py L155-L163).
- Meta webhook registration/OAuth callback and actual inbound canary are external runtime facts, not proven by source or synthetic tests.
- No real TTN/message/ad action performed.

## Existing validation entry points

Relevant tests already exist: test_direct_customer_automation.py; ai/test_direct_customer_data_extraction_helpers.py; integrations/meta_instagram/test_outbound_messaging.py, test_webhook_worker.py, test_direct_live_signals.py; test_order_fulfillment.py, test_order_fulfillment_api.py, test_order_fulfillment_workflow.py, test_order_fulfillment_finance.py; integrations/nova_poshta/test_durable_ttn_workflow.py; integrations/fulfillment/test_fulfillment_concurrency_postgres.py. This audit did not execute them.

## Open questions for the modernization scope

- Which order statuses count as sale, collected money and ad-attributed realized revenue? Current ProfitCalculationService includes NEW through COMPLETED unless refunded (L52-L83); actual attribution module is a separate audit.
- Should contact autofill be automatic with provenance or proposed-only? Current behavior/copy disagree.
- How should repeat orders attach to the same long-lived Direct conversation while preserving historical orders?
- Should the current sprint expose item cost explicitly before adding catalog defaults/migrations?
- How can saved order/TTN and a confirmed message draft form one recovery-safe seller workflow without bypassing provider gates or sending automatically?
