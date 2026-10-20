## `DirectIntelligenceService.analyze` in backend/app/ai/services/direct_intelligence_service.py (L17-L41)

**Purpose:** Existing provider-backed generic analysis persists product mentions and a suggested reply; it does not currently resolve catalog variants or prefill an order.

**Inputs & Assumptions:**
- Workspace/conversation/actor derived by MANAGER/OWNER route (api/v1/direct.py L186-L204).
- Conversation scoped get enforces workspace/deleted filtering; latest TEXT source retrieved (ai_direct_repository.py L34-L41,L161-L176). Latest source does not require INBOUND.
- AI workspace settings + global enabled flag preflight (L18-L24); preflight checks switches and configured limits, not a provider call (usage_service.py L9-L13).
- Context builder takes last max_messages from the full workspace-scoped conversation list, bounds text characters, includes direction/sender/type/text but NO message ID or timestamp (context_builder_service.py L6-L14).
- Structured model output is semi-trusted; Pydantic requires ProductMention text, allows quantity/color/size/SKU, no catalog IDs or per-mention confidence (structured_output.py L18-L37).

**Outputs & Effects:**
- AIAnalysis JSONB stores the full validated structured output, intent confidence and source_message_id, prompt/model/provider metadata (L27-L33; models/ai_direct.py L204-L234).
- Reply suggestion is created ONLY if suggested_reply exists; its structured_payload duplicates complete structured output (L34-L35). Product extraction must read AIAnalysis directly to support product mentions without reply.
- On provider/parse failure, function returns FAILED_SAFE analysis plus safe error code, sets conversation FAILED and records usage (L37-L41). HTTP request can succeed with FAILED_SAFE body because route commits and returns analysis (direct.py L198-L204).
- Preflight/missing source errors are raised before analysis row; route returns400 safe code (direct.py L200-L201).

**Block-by-Block:**

```python
# L18-L24
settings_obj = get_settings(); settings = self.ai_repo.get_or_create_settings(workspace_id)
conversation = self.conversations.get(workspace_id, conversation_id)
...
context = AIContextBuilderService(self.messages).build(...)
AIUsageService(self.ai_repo).preflight(...)
```
- **What:** Validates context and feature eligibility.
- **Why here:** No provider usage before basic readiness/context conditions.
- **Assumes:** Latest text and bounded context capture the relevant order.
- **Establishes:** Missing conversation/message causes explicit AIError.
- **Depended on by:** Source/provenance and extraction.

```python
# L27-L36
analysis = self.ai_repo.create_analysis(AIAnalysis(...status=PROCESSING...))
result = await self.gateway.generate_structured_response(...)
structured = DirectMessageAnalysisOutput.model_validate(result.structured_output)
analysis.status=COMPLETED; analysis.structured_result=structured.model_dump(mode='json')
...
if structured.suggested_reply: self.ai_repo.create_suggestion(...)
```
- **What:** One structured provider request is persisted.
- **Why here:** Processing record precedes request.
- **Assumes:** Model recognizes product text from conversation; exact evidence-to-message mapping: **nothing found**.
- **Establishes:** Product mentions are available regardless of whether a reply suggestion exists.
- **Depended on by:** Proposed product-to-order bridge.

```python
# L37-L41
except Exception as exc:
    code = getattr(exc, 'safe_code', 'AI_INVALID_STRUCTURED_OUTPUT')
    analysis.status=FAILED_SAFE; analysis.safe_error_code=code
    ...
return analysis
```
- **What:** Failure is a durable analysis state.
- **Why here:** Caller can distinguish empty extracted data from unavailable analysis.
- **Assumes:** UI inspects status, not HTTP success alone.
- **Establishes:** No order/customer/TTN is created by this function.

**Cross-Function Dependencies:**
- AIGatewayService maps timeouts/unexpected errors (ai_gateway_service.py L6-L15).
- OpenAIProvider missing key → AI_PROVIDER_NOT_CONFIGURED (openai_provider.py L32-L34); 401/403/429quota/rate/5xx map to safe codes L130-L145.
- AIRepository list_analyses filters workspace+conversation and newest-first L226-L236; get_analysis filters workspace L238-L244.
- Read APIs already expose full structured_result: GET direct/conversations/{id}/analyses (direct.py L207-L217), GET ai/analyses/{id} (ai.py L32-L36). Response includes prompt_key/status/source_message_id/created_at/safe_error fields (schemas/ai_direct.py L98-L125).
- Both contact extraction and generic analysis write AIAnalysis and latest_ai_analysis_id, so consumers must filter prompt_key DIRECT_MESSAGE_ANALYSIS, not simply latest analysis of any kind.
- Frontend AISuggestion type omits structured_payload and no typed analysis fetch exists (frontend/src/types/ai.ts L1-L2; services/ai.ts L1-L6; services/direct.ts L55).

**Open Questions:**
- Current source_message_id is one context anchor, not proof each product came from that message.
- Existing analyses have no context fingerprint; edits/new customer messages can make suggestions stale without an explicit freshness contract.
- Current generic prompt only instructs no invented products/prices/stock; does not impose the contact extraction prompt's INBOUND-only rule (prompts/registry.py L22-L37).
