## `DirectCustomerDataExtractionService._apply_data` in backend/app/ai/services/direct_customer_data_extraction_service.py (L350-L455)

**Purpose:** Applies extracted contact/delivery data to the linked customer; it does not create order items or TTNs.

**Inputs & Assumptions:**
- `data` is semi-trusted AI output normalized from Pydantic output (caller L281-L283). Manual apply retrieves a completed analysis with matching workspace/conversation/prompt (L123-L127).
- `overwrite_fields` comes from an allowlisted intersection for manual apply (L129-L138), or an empty set for auto-apply (L294-L302).
- Actor/workspace come from MANAGER routes for explicit calls (direct_customer_extraction.py L59-L76, L82-L99).
- Provider refs are established by directory lookup after resetting all flags/refs (L457-L498). Provider accuracy is an external service assumption.

**Outputs & Effects:**
- Ensures a prospect, fills eligible fields, may upsert default address, refreshes profile completeness, audits applied fields, returns field names (L360-L455).
- Flushes but does not commit; manual apply commits L142, extraction route commits direct_customer_extraction.py L75, worker commits runtime_worker.py L100-L102.

**Block-by-Block:**

```python
# L380-L394
if name and float(data.get("recipient_name_confidence") or 0) >= 0.85:
    if customer.name in GENERIC_CUSTOMER_NAMES or "name" in overwrite_fields: ...
if phone and float(data.get("phone_confidence") or 0) >= 0.9:
    if not customer.phone or "phone" in overwrite_fields: ...
if city and float(data.get("city_confidence") or 0) >= 0.8: ...
if region and (not customer.region or "region" in overwrite_fields): ...
```
- **What:** Field-specific confidence/overwrite gates.
- **Why here:** Existing data is considered before applying extracted values.
- **Assumes:** Numeric AI confidence represents reliability; no independent identity verification is done here.
- **Establishes:** Nonempty contact fields are preserved without explicit overwrite; region has no separate confidence threshold.
- **Depended on by:** Completeness calculation and audit.

```python
# L396-L427
can_apply_address = (
    data.get("delivery_provider") == CustomerDeliveryProvider.NOVA_POSHTA.value
    and data.get("city_verified") and data.get("warehouse_verified")
    and data.get("nova_poshta_city_ref") and data.get("nova_poshta_warehouse_ref")
    and float(data.get("warehouse_confidence") or 0) >= 0.85
)
```
- **What:** Address writes need provider verification and high warehouse confidence.
- **Why here:** Raw AI city/branch labels do not directly become verified delivery refs.
- **Assumes:** Verified refs still refer to the extracted city/branch. Directory lookup establishes current match (L471-L495).
- **Establishes:** Existing delivery address is changed only when missing or explicitly overwritten (L409-L412); name/phone/city must be present L413-L415.
- **Depended on by:** Later order wizard default address and TTN validation.

```python
# L430-L455
self.db.flush()
refreshed_state = self.customer_automation._state(...)
customer.profile_status = COMPLETE if refreshed_state.profile_complete else INCOMPLETE
if applied: self.audit_logs.create(...)
return applied
```
- **What:** Records actual changes and profile readiness.
- **Why here:** Completeness is computed after address/contact updates.
- **Assumes:** Caller commits or rolls back the unit of work.
- **Establishes:** Audit distinguishes automatic/manual source.
- **Depended on by:** Frontend extraction field badges.

**Cross-Function Dependencies:**
- `ensure_candidate`: workspace customer link; detailed record order-ensure-candidate.md.
- `_verify_delivery`: resets AI refs, resolves city/warehouse; on missing/unknown/non-NP data leaves flags false; on NovaPoshtaServiceError records verification unavailable (L457-L498).
- `_recent_messages`: last20 text messages in chronological order, workspace/conversation/deleted filtering L560-L579.
- `extract_now`: requires enabled flag/API credential, queues then invokes processing with auto_apply=true (L91-L106).
- `_process_analysis`: sets REVIEW_REQUIRED even after high-confidence autofill; catches failure and records safe status/usage (L247-L348).
- Shared state: same customer/address used by manual CRM and finalization.

**Open Questions:**
- UI says AI does not change CRM without confirmation (frontend/src/app/direct/page.tsx L698), while this path deliberately auto-fills eligible blanks (L294-L302); final copy/behavior policy needs a single product decision.
- Product mentions are present in generic AI schema (structured_output.py L18-L37), but this extraction schema is contact/delivery only (schemas/direct_customer_extraction.py L7-L30).
