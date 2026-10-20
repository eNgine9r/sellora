## `NovaPoshtaShipmentService.create_ttn` in backend/app/services/nova_poshta_service.py (L422-L607)

**Purpose:** Requests one provider document for a saved shipment while retaining durable operation state and resolving uncertain outcomes before retry.

**Inputs & Assumptions:**
- Workspace/shipment/actor; integration connection+decrypted API key required via settings service L428.
- Shipment row locked using workspace-aware repository/service L430, L856-L860.
- `_validate_for_ttn` ensures carrier/order/customer/name/phone/city/warehouse/value/sender fields L1162-L1201. Provider accepts configured sender and payload structure is an external assumption; sender verification contributes to write gate L110-L134.
- Real provider credentials/status were NOT inspected or exercised by this audit.

**Outputs & Effects:**
- May reuse existing result; persist WRITES_DISABLED; create a real Nova Poshta internet document; persist TTN; or require reconciliation.
- Success only binds a result with document ref and tracking number L586-L607.
- No Instagram outbound interaction in this function.

**Block-by-Block:**

```python
# L428-L475
connection, api_key = self.settings._require_connection(workspace_id)
shipment = self._get_shipment_for_update(workspace_id, shipment_id)
errors = self._validate_for_ttn(...)
if errors: return NovaPoshtaTtnResponse(success=False, ...)
if shipment.tracking_number or ...: return self._existing_result(shipment)
if not self._provider_writes_allowed(): ...
```
- **What:** Resolves local prerequisites, existing result, and permission gate.
- **Why here:** No external write before validation/reuse/readiness checks.
- **Assumes:** Caller understands a pre-existing TTN is reusable, not a new shipment event.
- **Establishes:** Environment capability, connected credential, verified connection, sender config, workspace permission all required (L110-L134, L1085-L1095).
- **Depended on by:** Provider phase.

```python
# L481-L528
operation = self._get_or_create_operation(...)
if operation.state in {COMPLETED, PROVIDER_ACCEPTED} and ...: return self._bind_provider_result(...)
if operation.state in {CALLING_PROVIDER, RECONCILIATION_REQUIRED}: return self._reconcile_operation(...)
operation.state = CALLING_PROVIDER
...
self.db.commit()
```
- **What:** Creates/reuses durable state and commits intent before external write.
- **Why here:** Provider timeout/process loss leaves a record to reconcile.
- **Assumes:** Provider marker search identifies the previous document.
- **Establishes:** One per-shipment/type operation with unique marker; get/create handles DB conflict L862-L895.
- **Depended on by:** All retry/failure paths.

```python
# L530-L607
payload = {**base_payload, "Description": operation.provider_marker}
try:
    result = client.create_internet_document(payload)
except NovaPoshtaClientError as exc:
    if exc.ambiguous: ...reconcile...
    ...FAILED_SAFE...
except Exception: ...reconcile...
if not result.tracking_number or not result.document_ref: ...reconcile...
return self._bind_provider_result(...)
```
- **What:** Makes provider call and classifies explicit refusal versus uncertainty.
- **Why here:** Call begins only after operation commit.
- **Assumes:** Client ambiguity classifier and provider response are accurate; actual network semantics not tested in this audit.
- **Establishes:** Ordinary explicit failure differs from unknown provider outcome.
- **Depended on by:** Fulfillment result retry rules.

**Cross-Function Dependencies:**
- `_reconcile_operation` L897-L947: searches marker over bounded date range; found result binds; missing result/search error marks manual reconciliation and blocks blind retry.
- `_bind_provider_result` L949-L1021: persists document refs/TTN, sets shipment CREATED, audits; local commit failure returns manual reconciliation, never reports normal success.
- `_provider_writes_allowed` L1085-L1095 delegates to nonsecret readiness gate; isolated legacy test fake branch is distinct from production repository path.
- External black box: Nova Poshta document create/find.
- Shared state: shipment provider fields and NovaPoshtaOperation; status sync later maps carrier statuses. ShipmentService maps IN_TRANSIT/DELIVERED/RETURNED into order status transitions (shipment_service.py L196-L217), which is separate from creating a TTN.

**Open Questions:**
- End-to-end provider canary, live sender settings, current readiness and status sync scheduling were not evaluated.
- “TTN created” should remain distinct from physically sent/delivered; create writes shipment CREATED (L972), later transitions handled elsewhere.
- TTN-to-Direct message drafting/send link: no caller found by bounded source search; wizard exposes copy TTN and return to Direct separately (wizard L289-L297).
