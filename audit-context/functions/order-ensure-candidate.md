## `DirectCustomerAutomationService.ensure_candidate` in backend/app/services/direct_customer_automation_service.py (L46-L110)

**Purpose:** Connects a Direct participant to a workspace customer/prospect. The webhook order-intent path and explicit UI action reuse it.

**Inputs & Assumptions:**
- Workspace/conversation IDs are caller-supplied UUIDs. Routes derive workspace membership and require MANAGER for ensure (backend/app/api/v1/direct_customer_automation.py L60-L75); webhook callers use the event's mapped workspace (inbound_message_service.py L47-L67, L232-L242).
- Actor may be null for automatic intake. `commit=False` means the caller owns the transaction (L103-L107).
- Existing conversation is enforced by `_conversation` (L220-L224), whose repository excludes deleted and foreign-workspace rows (ai_direct_repository.py L34-L41).
- Instagram identity is assumed suitable for choosing one customer. The repository uses scoped ID OR normalized username, earliest created match (customer_repository.py L27-L41); stronger conflict arbitration: **nothing found in this function/callee**.

**Outputs & Effects:**
- Creates a PROSPECT/INCOMPLETE customer without phone, reuses a matching one, or returns no customer when the optional intent gate does not match (L55-L82).
- Links the conversation, writes audit records, commits or flushes, returns state including whether automatic creation happened (L83-L110).

**Block-by-Block:**

```python
# L55-L58
conversation = self._conversation(workspace_id, conversation_id)
latest = self.messages.latest_analyzable(workspace_id, conversation_id)
if require_order_intent and not detect_direct_order_intent(latest.text if latest else None).detected:
    return self._state(workspace_id, conversation, None)
```
- **What:** Optional deterministic order-intent gate.
- **Why here:** Avoids creating a customer before deciding intake qualifies.
- **Assumes:** Latest analyzable TEXT represents purchase intent. Callee filters workspace/conversation/TEXT/deleted rows, but not direction (ai_direct_repository.py L161-L176).
- **Establishes:** No writes on a nonmatch.
- **Depended on by:** Manual callers use false; inbound caller separately gates its actual received text (L112-L126).

```python
# L60-L82
existing = self.customers.get(workspace_id, conversation.linked_customer_id) if conversation.linked_customer_id else None
customer = existing or self.customers.find_by_instagram_identity(...)
if customer is None:
    customer = self.customers.create(Customer(...))
```
- **What:** Reuse linked/matched customer before creating prospect.
- **Why here:** Preserves established customer identity.
- **Assumes:** Identity equality identifies the same person; arbitration noted above.
- **Establishes:** Customer belongs to workspace; get/match queries enforce it (customer_repository.py L23-L41), newly created row takes workspace L71.
- **Depended on by:** Conversation link and state calculation.

```python
# L94-L110
conversation.linked_customer_id = customer.id
self.audit_logs.create(...)
if commit:
    self.db.commit()
    self.db.refresh(customer)
else:
    self.db.flush()
```
- **What:** Persists association and audit.
- **Why here:** Customer exists before relationship write.
- **Assumes:** Caller handles rollback for noncommitted mode; API route does (direct_customer_automation.py L76-L78), worker transaction wrapper does (runtime_worker.py L55-L63).
- **Establishes:** Returned state reflects customer/contact/address completeness, not purchase/shipment success (`_state`, L226-L260).
- **Depended on by:** Direct card and order wizard initial customer selection.

**Cross-Function Dependencies:**
- `detect_direct_order_intent` (internal): pattern matching for explicit verbs plus limited COD/product context (direct_order_intent_service.py L14-L57); does not select catalog SKU.
- `_sync_identity` (internal): fills missing scoped ID/username, generic display name, source only (L262-L273).
- `_state` (internal): reads addresses, requires city+warehouse provider refs for delivery completeness, returns one linked order (L226-L260).
- Callers: webhook `ensure_from_inbound_order_intent`; extraction auto-apply; API ensure; order finalization.
- Shared state: customer identity, conversation.linked_customer_id; finalization also writes linked_order_id.
- Coupling: creating a prospect does not create order, reserve inventory, or send a message.

**Open Questions:**
- Concurrent customer creation/deduplication under multiple events needs a separate model/transaction review.
- One `linked_order_id` per conversation represents the current UI relation; repeated purchases in the same Instagram thread need explicit product behavior.
