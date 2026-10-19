## `send_reply` in backend/app/api/v1/direct.py (L259-L324)

**Purpose:** Sends an explicitly confirmed Instagram text using a durable idempotent operation. Relevant future recipient of a prepared TTN message.

**Inputs & Assumptions:**
- MANAGER role and derived workspace enforced by dependencies L267-L269.
- Body message/human-agent flag; Idempotency-Key required L271-L272.
- User intentionally requests sending; no automatic call from order/TTN path found in bounded source search.
- Token encrypted at rest and decrypted only in service.call_provider (outbound_message_service.py L62-L73). Credentials were not read in this audit.

**Outputs & Effects:**
- Prepares durable message operation; may return existing operation without new provider call; otherwise calls Meta, persists outbound message or failure status.
- Returns HTTP response containing operation status, provider ID, direct message ID; a returned response is not equivalent to COMPLETED (L315-L324).

**Block-by-Block:**

```python
# L273-L298
prepared = service.prepare_operation(...)
db.commit()
if not prepared.should_call_provider:
    return ReplySendResponse(...)
```
- **What:** Saves send intent and reuses a prior key.
- **Why here:** External call occurs only after durable operation.
- **Assumes:** Browser keeps the same key for retrying one send intention.
- **Establishes:** Service matches request fingerprint, rate limits, validates send flag/window/recipient/connection/token (outbound_message_service.py L26-L61, L101-L113).
- **Depended on by:** No duplicate provider call for same key.

```python
# L299-L324
try:
    result = await service.call_provider(...)
    operation = service.finalize_success(...)
    db.commit()
    ...
except MetaInstagramError as exc:
    operation = service.finalize_failure(...)
    db.commit()
    return ReplySendResponse(...)
```
- **What:** Sends and records success/failure state.
- **Why here:** Preparation and provider phases have separate committed checkpoints.
- **Assumes:** Caller evaluates returned operation status.
- **Establishes:** Provider accepted message is persisted once by provider ID (outbound_message_service.py L74-L87); ambiguous failure becomes reconciliation, throttled/unavailable becomes retry, explicit failure becomes FAILED_SAFE (L88-L98).
- **Depended on by:** UI composer should distinguish sent versus pending/reconciliation/error.

**Cross-Function Dependencies:**
- `prepare`: send global flag, nonsynthetic recipient/scopedID, 24-hour messaging window or enabled valid human-agent window, 1000-character limit (outbound_message_service.py L26-L41).
- `prepare_operation`: connected account, token presence/expiry, savepoint insert + conflict reread L42-L61.
- `call_provider`: token decryption, DB commit, external Meta send_text_message L62-L73. Provider response/current policy not exercised.
- `finalize_success` / `finalize_failure`: described above.
- Browser currently generates a fresh random key on every mutation invocation and clears composer on every response success callback, without examining returned status (frontend/src/app/direct/page.tsx L118-L126).
- Shared state: MetaMessageOperation, DirectMessage, conversation outbound timestamps.

**Open Questions:**
- UI error/retry/reconciliation presentation needs checking against all returned operation statuses; current browser onSuccess path unconditionally clears text.
- A TTN-specific draft should be based on verified order/shipment linkage; no such endpoint/caller found in inspected paths.
- Actual Meta connection and messaging canary remain runtime gates; this audit did not send anything.
