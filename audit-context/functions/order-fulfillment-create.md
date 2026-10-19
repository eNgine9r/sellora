## `OrderFulfillmentService.create` in backend/app/services/order_fulfillment_service.py (L271-L385)

**Purpose:** Creates customer/address as needed, order with reserved inventory, shipment draft, then optionally requests Nova Poshta TTN. Separates saved CRM/order from provider uncertainty.

**Inputs & Assumptions:**
- Validated `OrderFulfillmentCreate`, workspace, actor; MANAGER route calls service (backend/app/api/v1/order_fulfillments.py L24-L37).
- Idempotency key identifies one payload. `_prepare_operation` locks/reuses key; mismatched fingerprint conflicts except failed-safe with no order; concurrent unique-key conflict is reread (L387-L417).
- Cost/price/quantity are supplied item snapshots. The wizard explicitly supplies `unit_cost: 0` (frontend/src/features/orders/components/order-fulfillment-wizard.tsx L265). No Product/ProductVariant catalog cost exists in inspected models (product.py L8-L19; product_variant.py L12-L25).

**Outputs & Effects:**
- Saved order/customer/address/shipment and durable operation; optional real provider document creation.
- Possible result: ORDER_AND_TTN_CREATED; ORDER_CREATED_TTN_PENDING; ORDER_CREATED_PROVIDER_RECONCILIATION_REQUIRED (L327-L385).
- Does not send Instagram message, does not itself link a source Direct conversation. Wizard performs a second finalization request after success (wizard L107-L126).

**Block-by-Block:**

```python
# L272-L288
fingerprint = self._fingerprint(payload)
operation, replay = self._prepare_operation(...)
if completed_result and operation.order_id and operation.shipment_id and (...):
    return self._stored_response(..., idempotent_replay=True)
```
- **What:** Replays completed work; pending TTN may continue on retry.
- **Why here:** Prevents creating new business records for an existing operation.
- **Assumes:** Stored operation IDs represent committed local work.
- **Establishes:** Stable key cannot silently change completed order payload.
- **Depended on by:** Frontend retry controls.

```python
# L300-L321
if not operation.order_id or not operation.shipment_id:
    try:
        customer_id, address_id = self._create_business_records(...)
        ...
        self.db.commit()
    except (...):
        self.db.rollback()
        ...
        raise OrderFulfillmentValidationError(str(exc)) from exc
```
- **What:** Local business records commit before provider call.
- **Why here:** Order survives provider failure; no open uncommitted order across network call.
- **Assumes:** OrderService creates correct reservations and financial snapshots.
- **Establishes:** Customer/address/order/shipment local success all persist together; rollback path marks failure only when no order (L313-L320).
- **Depended on by:** TTN phase and result rendering.

```python
# L327-L385
if not payload.create_ttn: return self._complete(...ORDER_CREATED_TTN_PENDING...)
try:
    ttn = self.nova_poshta_service_factory(self.db).create_ttn(...)
except NovaPoshtaServiceError: return self._complete(...ORDER_CREATED_TTN_PENDING...)
if ttn.success and ttn.tracking_number: ...
if ttn.manual_reconciliation_required or (...): ...
```
- **What:** Optional provider phase, persisted local order regardless of provider result.
- **Why here:** Avoids treating a provider timeout as a failed order.
- **Assumes:** Nova Poshta response flags distinguish explicit refusal from uncertain state.
- **Establishes:** Ambiguous provider result disables ordinary retry; disabled writes remain a pending TTN path.
- **Depended on by:** Wizard shows copy/retry/reconciliation actions.

**Cross-Function Dependencies:**
- `_create_business_records` L419-L525: scoped existing customer lookup or CustomerService create(commit=false); address update/create(commit=false); OrderService.create(commit=false); ShipmentService.create(commit=false). Order/shipment IDs attached to operation.
- `OrderService.create` L63-L137: validates workspace customer/campaign/active variants; locks inventory; aggregates duplicate variant quantities before availability test L69-L82; snapshots item payload prices/costs L106-L123; writes RESERVE transaction L125-L126; sums cost/revenue and canonical profit L127-L129.
- `NovaPoshtaShipmentService.create_ttn`: durable provider operation, write gates, reconciliation; see order-ttn-create.md.
- `_stored_response` L536-L556: serializes linked business records and response state.
- Shared state: OrderFulfillment, order, shipment, inventory reservations. Existing-order prepare/execute APIs are also on same service L55-L260.

**Open Questions:**
- No enforced nonzero/known purchase cost: schema allows default0 (schemas/order.py L10-L14); OrderService trusts it L108/L120. Zero can be legitimate; model has no separate unknown-cost flag.
- Wizard's estimate uses total minus only shipping/ad/COD/other costs (L177-L180, L360), consistent with current0 payload but not a purchase-cost-aware estimate.
- Direct association is an independent second request; browser interruption after create can leave a saved order and unlinked conversation. Warning is displayed for caught finalization failure (wizard L124-L126).
- Full concurrent operation safety is outside this bounded function record; existing PostgreSQL concurrency tests exist.
