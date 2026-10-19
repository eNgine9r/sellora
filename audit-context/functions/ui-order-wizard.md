## OrderFulfillmentWizard in frontend/src/features/orders/components/order-fulfillment-wizard.tsx (L34-L375)

**Purpose:** Create an order with verified recipient/product/payment data and optional Nova Poshta TTN, using existing consolidated endpoint.

**Inputs & Assumptions:**
- workspaceId and lists from OrdersPage; semi-trusted server data.
- initialCustomerId/sourceDirectConversationId: URL-derived and validated client against fetched customers by OrdersPage L212-L217.
- Phone normalized preview accepts UA10 or38012 digits (L25-L31).
- Assumes inventory shown to user still current; server must enforce atomic reservation, delegated audit.
- Assumes total-costs is an adequate estimated-profit preview; product cost absent in this UI expression L180,L360. Backend snapshots not inspected here.

**Outputs & Effects:**
- Fetches customer addresses and NP readiness (L95-L104).
- Creates fulfillment with stable idempotency key per component/workspace; submit lock L60-L62,L137-L143,L241-L276.
- On success separately finalizes Direct linkage/profile; catches failure and displays warning L107-L129.
- Can create order without TTN or request order+TTN if readiness allows L369-L371.

**Block-by-Block:**
- L145-L169: initial customer then default address populate form. User edits while address refetches remain open question.
- L190-L208: customer selection clears delivery fields; variant selection fills price.
- L211-L239: step validation requires customer/recipient/phone and verified NP refs before product step; verifies selected variants and stock display before review.
- L241-L276: submit lock, validation, payload includes campaign_id optional, create_ttn flag and unit_cost0. Backend determines business implications.
- L279-L299: result code distinguishes success/reconciliation, exposes TTN/copy/returnDirect/openOrder/openShipment. Clipboard action here has no visible failure handling; shared CopyTtnButton handles it elsewhere.
- L303-L371: three-step progress, bounded scroll body and sticky footer; recipient first, product/payment second, totals/readiness third.

**Cross-Function Dependencies:**
- createOrderFulfillment: server workflow boundary, delegated domain audit. No provider invocation made in audit.
- finalizeDirectCustomerOrder: separate POST after creation L111-L123; linkage failure surfaced.
- CitySearchSelect/WarehouseSearchSelect: provider lookup components; only caller contract examined.
- OrdersPage L340-L368: wizard mounted in shared FormDialog and invalidates related caches.
- ShipmentsPage L91-L113: order_id query requests create form; its workspace reset effect clears creation state. Wizard's openShipment target uses this query (L297).
- CopyTtnButton source inspected ttn-actions.tsx L15-L22, handles clipboard success/failure only; not send to customer.

**Open Questions:**
- Should existing shipment result link target shipment ID/read mode rather than create mode? Need coherent route intent.
- TTN-to-Direct reply preparation absent from audited result. Need backend linkage/send contracts before any action.
- Profit preview excludes item costs while payload sends unit_cost0; domain service may snapshot cost. Do not claim persisted profit wrong without tracing.
- Header create order /orders navigation does not open wizard; requestedCreate effect requires customer_id (orders/page.tsx L212-L217).
