# Direct product → order bridge — bounded context and implementation blueprint

Date2026-10-19. Source inspected on codex/2026-10-19-direct-sales-workspace before implementation of this bridge. No model requests, runtime data reads, credentials, order writes or provider actions. This is a primary requested user workflow, not an optional future idea. Application files not changed.

## Existing path and missing connection

| Step | Existing contract | Evidence |
| --- | --- | --- |
| Extract mentions | Generic structured ProductMention has text,quantity,color,size,SKU; max20 mentions, quantity1..999; no variant ID, per-mention confidence or message IDs | backend/app/ai/schemas/structured_output.py L18-L37 |
| Persist | Full typed output stored in AIAnalysis.structured_result JSONB; source_message_id, prompt, status, intent confidence and timestamps retained | backend/app/ai/services/direct_intelligence_service.py L17-L41; models/ai_direct.py L204-L234 |
| Read | GET /direct/conversations/{id}/analyses newest-first workspace+conversation; GET /ai/analyses/{id} workspace-scoped | api/v1/direct.py L207-L217; api/v1/ai.py L32-L36; repositories/ai_direct_repository.py L226-L244 |
| Optional reply | AISuggestion duplicates structured output only when suggested_reply exists; therefore suggestions are incomplete as product extraction source | direct_intelligence_service.py L34-L35; schemas/ai_direct.py L128-L143 |
| Match | ProductMatchingService exists but no runtime caller found. It selects first title match, fixed score0.9/0.65, never chooses variant, alternatives empty | ai/services/product_matching_service.py L15-L25 |
| Catalog | /products?search searches name/productSKU; /products/variants?product_id lists variants; both require ANALYST membership, queries scoped workspace+softdelete | api/v1/products.py L20-L32; repositories/product_repository.py L18-L29,L52-L70 |
| Order entry | Orders already loads products/variants/inventory; Direct params only prefill customer/sourceconversation. Wizard items always begin blank, no initialitems prop | frontend/src/app/orders/page.tsx L85-L118,L348-L358; order-fulfillment-wizard.tsx L34-L79,L145-L169 |
| Save | Wizard sends ordinary OrderItemCreate to existing idempotent fulfillment service; backend validates active variant/customer/workspace/stock again | wizard L241-L276; backend order_service.py L69-L82,L298-L314 |

Detailed records: functions/order-product-analysis.md and functions/order-product-matching.md.

## Critical source/freshness constraints

- Filter DIRECT_MESSAGE_ANALYSIS explicitly. Contact extraction writes the same AIAnalysis table and latest_ai_analysis_id; taking first analysis of any prompt can yield delivery data instead of products.
- source_message_id is the latest analyzable TEXT of either direction (ai_direct_repository.py L161-L176), not a citation proving each mention appeared there.
- Existing generic context has direction/sender/type/text only, no message IDs or timestamp (context_builder_service.py L6-L14). Model's product_mentions.text may be a summary, not a verbatim quote. UI may show “AI розпізнав: …” and an analysis context anchor; never present it as a verified quote from a particular customer message.
- Generic prompt SAFETY_RULES forbids invented products/prices/stock, but does not carry contact extractor's explicit INBOUND-only rule (prompts/registry.py L22-L37).
- Existing analyses lack source fingerprint; newer customer messages and message edits can invalidate earlier proposals. Do not silently substitute an old completed analysis when newest generic attempt failed or conversation changed.
- A direct exact SKU/title substring found in an INBOUND message can be cited honestly with that actual message ID/text. If no exact source evidence is found, mark product proposal as requiring review; no invented source citation.

## Smallest coherent implementation now — no migration

1. Add one provider-free read service/route, preferably GET /direct/conversations/{conversation_id}/order-proposal, with ANALYST read access and workspace conversation validation. It reads saved analyses, current relevant inbound text, catalog and availability; does not call a model or mutate customer/order/inventory. Keep matching in services, query construction in repositories.
2. Reuse and extend ProductMatchingService rather than invent parallel rules. Add mention-aware matching to an active, nondeleted product+variant catalog. Require workspace on every lookup. Casefold/trim SKU and attributes; return explicit matches, alternatives, reasons, quantities and source metadata.
3. Response can be typed proposal with analysis_id/prompt_key/created_at/source_message_id, analysis_status/safe_error_code, is_stale or evidence_verified, plus lines {mention_text,quantity,match_status,matched_by,candidates,selected_variant_id,price,availability,source_message_ids}. Existing JSON data can be read without migrations. AI intent_confidence is separate from catalog rule score; do not display fixed matching scores as probability AI selected right product.
4. Deterministic matching rules: unique exact variantSKU wins only when supplied attributes do not contradict it. An explicit unknown/conflicting SKU stays unresolved; do not quietly choose a similarly named product. Otherwise exact normalized product title/productSKU plus provided color/size narrows active variants. Multiple remaining variants are AMBIGUOUS; do not select newest/first. Missing price or inventory is explicitly unknown. Current OrderService still performs final validation and locking.
5. Useful provider-free fallback: detect exact catalog variantSKU in recent INBOUND text with token boundaries, attach real message ID and label “Артикул із повідомлення”. This is deterministic text matching, not an AI success. Never infer purchase solely from manager text or an ambiguous partial SKU. Deduplicate repeated mentions conservatively; do not sum the same repeated shopping reference into extra units without evidence.
6. Render a compact “Товари з діалогу” block inside the existing Orders wizard when sourceDirectConversationId exists. Fetch proposal using workspace+conversation query key. Show recognized mention, source, reason, candidate name/SKU/color/size/currentprice/stock and editable quantity. Manager explicitly applies selected candidates; default unanswered ambiguous rows remain unselected. Existing manual item selection remains available.
7. Carry the selected proposal into existing wizard items, not into a new order API. Add/apply items only when user clicks “Додати до замовлення”; no effect overwrites edited items after refetch or workspace/conversation switch. Revalidate current active variant/price against loaded catalog, do not take provider price; preserve new unit_cost UI work by root.
8. Keep existing Direct link to Orders; Orders fetches proposal from server using conversation ID. No product JSON, PII or AI payload in query parameters/localStorage. No additional writes or new AI calls just by opening the wizard.
9. If no saved analysis/exactSKU or analysis failed/disabled: show honest state and manual selection. Existing explicit “Аналізувати діалог” can call current generic analyze only after user action and readiness checks; inspect returned status, invalidate proposal on COMPLETED. Do not fake products or claim model ran.

Frontend implementation can read existing analyses+catalog endpoints directly to avoid new backend deploy, but that duplicates server-side matching/payload validation. Preferred service route uses existing architecture and provides one testable contract; no migrations needed either way.

## Provider readiness and failures without reading secrets

- GET /ai/health already returns feature_configured,provider_selected,credential_present,ai_enabled,safe_configuration_status; key value is never returned (backend/app/api/v1/ai.py L17-L20; schemas/ai_health.py L4-L9).
- GET /ai/settings also exposes direct_intelligence_enabled and limits (ai.py L22-L24; schemas/ai_direct.py L155-L169). Health CONFIGURED means switches/key presence, not valid key, budget or reachable provider. Health handler uses get_or_create settings; this audit did not call it.
- Explicit analyze preflight can raise AI_FEATURE_DISABLED, AI_INPUT_TOO_LARGE, AI_DAILY_LIMIT_EXCEEDED (usage_service.py L9-L13), returned HTTP400 by direct route L200-L201.
- Provider may produce FAILED_SAFE analysis with HTTP200, safe_error_code and safe_error_message (direct_intelligence_service.py L37-L41; direct.py L202-L204). Typed frontend runDirectAnalysis currently returns unknown and existing UI primarily invalidates reply suggestions (services/direct.ts L55; Direct page current analysis mutation).
- OpenAIProvider maps missingkey,invalidkey,forbidden,billingquota,rate,unavailable,invalidoutput into safe codes (openai_provider.py L32-L34,L104-L110,L130-L145). New UI should localize these into seller language, e.g. recognition unavailable/use manual selection; OWNER can get settings link. Never tell ordinary seller to edit backend secrets.
- Saved proposals remain readable when AI is disabled. Opening/refreshing proposal must never invoke provider or claim configured means functional.

## Necessary focused tests and acceptance checks

- Matching: exactSKU with case/spacing; name+color+size unique; duplicate product titles; multiple variants; contradictory/unknown SKU; inactive/deleted/otherworkspace product/variant; missingprice/inventory; no “first candidate” selection.
- Evidence: model mention without exact INBOUND quote stays unverified; manager-only text is not a confirmed customer choice; exactSKU fallback cites actual inbound ID; bounded matching does not match SKU fragment inside a larger identifier; repeat references do not double quantity.
- Proposal: noanalysis, FAILED_SAFE newest, wrongprompt, stalecontext, COMPLETED with no suggested_reply, malformed/empty structured JSON, crossworkspace conversation/analysis, analyst read versus forbidden writes. Assert no gateway/provider call and no order/stock changes on GET.
- Wizard: loading/empty/error, explicit apply, multiple product quantities, ambiguous candidate selection, manual fallback, proposal refetch preserves edits, workspace/conversation change clears proposal state, ordinary fulfillment payload/stock check unchanged.
- Verify desktop/mobile with safe local fixtures, then existing typecheck/lint/build and relevant backend tests. Current test_ai_foundation only tests default ProductMatchResult and schema; it does not exercise matcher (tests/ai/test_ai_foundation.py L29-L32).
- Acceptance: customer speaks SKU or analysis has grounded product mention → manager sees catalog proposal with source → applies/reviews line → existing order+TTN flow; no automatic send, stock reserve or TTN during recognition.
