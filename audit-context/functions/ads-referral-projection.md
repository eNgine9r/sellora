## InstagramInboundMessageService._metadata in backend/app/integrations/meta_instagram/services/inbound_message_service.py (L297-L300)

**Purpose:** Reduces provider message/postback objects to metadata stored on DirectMessage.

**Inputs & Assumptions:**
- message/postback: untrusted provider dictionaries derived by _process_item from item.message/item.postback (L80-L83), after process_event checks workspace connection readiness (L47-L57).
- Caller supplies mappings as expected; malformed nested payload validation beyond this function not reviewed.
- Advertising referral survives the projection: **nothing found**. Function receives message and postback only, not the full webhook item.

**Outputs & Effects:** Dictionary of booleans; no external calls or direct state writes.

**Block-by-Block:**

```python
# L297-L300
def _metadata(self, message: dict[str, Any], postback: dict[str, Any]) -> dict[str, Any]:
    if postback:
        return {"postback_payload_present": bool(postback.get("payload"))}
    return {key: True for key in MEDIA_TYPES if message.get(key)}
```

- **What:** Postback branch retains payload presence; otherwise retains media-type presence.
- **Why here:** Called once during DirectMessage construction at L137.
- **Assumes:** Media/postback-presence is sufficient for metadata consumer needs.
- **Establishes:** No external ad_id, referral ref, campaign ID, click ID, referral timestamp or attribution evidence is projected.

**Cross-Function Dependencies:**
- No callees beyond dict/bool.
- MEDIA_TYPES at L29-L35 includes image/video/audio/sticker/share.
- _process_item (L69-L167) handles read/reaction/edit branches first, deduplicates provider_message_id, obtains conversation, constructs message, then profile/customer enrichment for inbound. It does not read referral/ad_id.
- _conversation (L244-L265) creates or finds participant-scoped Instagram conversation, not campaign touch.
- DirectConversation schema (`models/ai_direct.py:L149-L177`) has lead/customer/order links and provider identity fields but no ad/campaign/touch fields.
- DirectMessage has generic attachment_metadata JSONB (`models/ai_direct.py:L180-L200`).
- Full webhook payload is the upstream event input to process_event at L60; this audit did not query persisted payloads or live traffic.

**Open Questions:**
- Does this particular Instagram provider/product emit ad referral under top-level item, nested message, or separate event? Needs authoritative provider schema plus sanitized fixture.
- What evidence policy should allow campaign inheritance into lead/order? No recorded policy found in these models/services.
- Should returning customers accumulate touches while original order evidence remains immutable? Current model has no touch ledger.
