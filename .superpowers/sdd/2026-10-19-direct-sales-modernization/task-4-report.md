# Task 4 — products from Direct into the existing order wizard

Status: IMPLEMENTED; root-owned exact-SHA production/browser/CI and independent review pending.

## Summary
- New provider-free authenticated ANALYST GET /api/v1/direct/conversations/{conversation_id}/order-proposal validates workspace conversation first and reads saved generic analyses, bounded inbound text, active scoped catalog and batched inventory. It creates no settings, customer, order, stock reservation, shipment or provider call.
- Reused ProductMatchingService with deterministic normalized exact variant SKU priority, then known parent SKU or exact product title/SKU plus supplied attributes. Unknown explicit SKU never falls back to similar title. Whitespace-only optional attrs are absent. Duplicates stay ambiguous; no first/newest candidate or confidence probability.
- Only the latest DIRECT_MESSAGE_ANALYSIS attempt participates. Newest failed/pending/malformed attempt does not resurrect prior success; full saved product_mentions structure is required, while a valid empty list/no reply remains valid. Storage created/updated/deleted timestamps conservatively flag context changes, including imported messages with old provider timestamps.
- Saved-analysis mentions are context-only and always require deliberate review and variant selection. Separate exact INBOUND SKU lines cite an actual message and matched text snippet, default quantity1 and deduplicate repeats. Manager/outbound/deleted text provides no fallback evidence.
- Existing wizard renders localized loading/missing/stale/failed/malformed/pending/error/manual states and explicit Apply. It validates active current catalog, quantity, stock and sale price again, skips existing variants, preserves edited price/cost/campaign/items across refetch/repeat Apply, and resets on source/workspace context changes. Unknown catalog price requires explicit manual entry, including ordinary manual selection.
- Existing Direct analysis action now checks COMPLETED, treats HTTP200 FAILED_SAFE as failure, and invalidates proposal/suggestions only on success. Opening/refetching a proposal never analyzes.
- Preserved Task2 draft/revision/send/TTN/scroll guards, cost review and Task3 campaign selection. No migrations, dependencies, provider/key changes or public enum changes.

## Read contract / bounds
Schema: backend/app/schemas/direct_order_proposal.py.
Response: conversation_id; nullable analysis_id/created_at/context_message_id; analysis_state MISSING/COMPLETED/STALE/FAILED/MALFORMED/PENDING; catalog_truncated/context_truncated; lines.
Line: id, mention_text, quantity1..999, source ANALYSIS_CONTEXT/INBOUND_SKU, evidence[{message_id,snippet}], requires_review, match_status MATCHED/AMBIGUOUS/NOT_FOUND, matched_by, reason, candidates_truncated, candidates.
Candidate: product_id, variant_id, product_name, SKU/color/size, nullable current price and available_quantity. No customer profile, settings, provider payload, model credentials or fabricated cost.
- Catalog query joins both scoped, active, nondeleted products/variants, loads at most501 rows. Sentinel >500 disables matching explicitly (CATALOG_LIMIT); partial catalogs never establish uniqueness.
- At most50 recent inbound messages, 4000 chars each/20000 total; max20 saved mentions +20 distinct inbound SKU lines; max10 displayed candidates, retaining ambiguous status if alternatives truncated; snippet max160.
- Exact security inventory reconciled to217 total,198 workspace-scoped,122 mutations unchanged; dedicated route test proves authenticated ANALYST read dependencies.

## Checks run
- Isolated safe helper invoked through bash (script not executable): bash /home/btcradar/runtime/sellora/run-focused-backend-tests.sh -q --tb=short tests/test_direct_order_proposal.py tests/ai/test_ai_foundation.py tests/ai/test_latest_analyzable_repository.py tests/security/test_endpoint_inventory.py
  Final result:51 passed, one existing httpx/Starlette deprecation warning,7.80s pytest /14.08s process. Disposable SQL tables exercise actual repositories/service/API; SELECT-only GET and settings/provider-call sentinels verify no writes/calls.
- Initial focused run exposed a test seed helper argument named model colliding with AIAnalysis.model; renamed the helper argument and reran. Earlier checkpoints43/46/49 passed;51 is final backend count.
- npm run typecheck && npm run lint && npm run mobile:audit:static: passed,29 routes/zero shared-overlay exceptions,14.85s. Final type/lint after the last manual-null-price/refetch guard changes is recorded below.
- Orders/inventory/shipments static24 checks; Direct AppShell18 checks; Meta Instagram23 checks: passed.
- node --check on direct-workspace-browser.mjs, fulfillment-browser-fixture.mjs, order-proposal-browser-scenarios.mjs; git diff --check: passed.
- No production build/browser or full CI on the live Pi. Root owns isolated exact-SHA build/browser and canonical CI.

## Behavioral coverage authored
Canonical existing fail-closed browser harness imports new proposal scenarios, preserving earlier Task1–3 suites.
-375/390/1280/1440 Direct→wizard→SKU Apply→cost/price/campaign edits→refetch/repeat Apply→review actual payload→verified TTN draft with preserved manual draft/confirmation; no automatic analyze/send.
- Invalid/overflow quantity/stock; stale ambiguous AI starts unselected, requires manual review; unknown price requires explicit entry; ordinary manual fallback remains.
- Loading, missing, failed, malformed, pending/error states; late prior-conversation proposal response cannot populate new wizard; HTTP200 FAILED_SAFE explicit analysis surfaces failure.
Browser scenarios are authored/syntax-checked but not yet executed; root runtime selectors/fixture evidence remain pending.

## Files changed
Backend matcher, thin Direct route, existing catalog/message/analysis repositories, typed proposal schema/service, actual SQL proposal tests and exact endpoint security inventory.
Frontend wizard/proposal component/types/service, scoped Direct success handling, wizard context key, uk/en dictionaries and existing browser fixture/harness plus proposal scenario module.
Root-owned deploy/raspberry/verify_target.py is excluded.

## Limits / follow-up
- Because actual SKU schema permits arbitrary characters, inbound fallback intentionally requires whole whitespace-delimited literal SKU references. Quoted/punctuation-attached references are conservatively unresolved; tests reject them and larger identifiers, and manual selection remains available.
- Catalogs over500 active variants deliberately fall back to manual selection; a later exact server-filtered strategy can support larger catalogs without weakening uniqueness.
- Freshness is conservative on stored message timestamps (no source fingerprint/migration). It may require re-review for a non-text metadata update; it never invents exact per-mention AI evidence.
- No claim of live Instagram recognition/provider availability, automatic products/orders/TTNs/messages, or deployment completion.

## Final self-review corrections / freeze checks
- A fresh proposal price now reaches the wizard exactly as displayed instead of being replaced by the older page catalog price. Null proposal price uses the explicit manual value even if the cached variant still has an old price; catalog identity/active/stock checks remain. Browser drift case covers proposal130/catalog100 and proposal-null/manual123/catalog300, then reapply preserves existing manual177/cost40 and actual payload.
- Proposal Apply is disabled and guarded during refetch/error; old TanStack data never remains actionable as a freshly verified proposal. Existing wizard items stay intact.
- Prefix clipping cannot manufacture a SKU boundary: an incomplete terminal token is discarded using the original following character. Actual SQL/service regressions cover both the4000-per-message and20000-total budget ending inside SKU-1-RED; no SKU-1 evidence is fabricated.
- Parent product SKU + attributes and normalized-empty optional attrs are explicitly tested, preserving exact variant-SKU priority and true-unknown-SKU refusal. Saved nested product_mentions keys are mandatory, distinct from valid empty lists.
- Final frontend typecheck/lint after price/refetch fixes: exit0,16.24s. Final backend51 cases passed as above; final browser-module syntax/diff checks passed. Final mobile/operational static reruns are recorded in the scoped commit preparation output. No full build/browser/CI claim.

## Independent review / runtime correction — round 1
- Review I1 confirmed: stable analysis-line IDs preserved a boolean acknowledgement through newly STALE and subsequent already-STALE proposal refreshes. Consent now records the successful query snapshot (dataUpdatedAt plus monotonically incremented dataUpdateCount), not merely line identity. The checkbox derives current consent from that snapshot; Apply re-reads the live scoped query-cache version to reject an old acknowledgement even before a refresh render settles. Identical structurally shared payloads and same-millisecond responses cannot reuse old consent.
- Pending variant/quantity/manual price values and all already-applied wizard items remain untouched by refresh. No backend/API/provider behavior or Task1–3 guard changes.
- Added a browser scenario that applies an inbound item, manually edits its price177/cost40/quantity2/campaign, then reviews an unapplied COMPLETED AI line. Same-ID STALE refresh requires new acknowledgement; a second identical already-STALE refresh again requires new acknowledgement. Pending variant/quantity remain, old item edits are asserted unchanged, and renewed consent explicitly applies the additional item.
- Root exact96064e2 evidence: six backend/static/security/PG/mobile CI jobs passed and production build passed; canonical browser failed only at the first proposal scenario's exact campaign-label select. Independent edge build passed and reproduced that same timeout. Inspected synthetic log plus actual implicit label/dictionary: select options contribute to its accessible name. Replaced exact getByLabel with an asserted combobox/localized-name prefix, retaining actual campaign-ID selection and preservation assertions. Other new locator labels were checked against current dictionaries/widgets.
- Fresh focused frontend npm run typecheck && npm run lint: exit0,13.32s. New scenario module node --check and git diff --check passed. Mobile static:29 routes, zero shared-overlay exceptions, PASS. Backend unchanged; no repeat of the51 focused cases. New exact-head browser/build/CI/re-review remain root-owned and pending; no full browser-pass claim.

## Runtime fixture correction / bounded rerun mode — round 2
- Root exact4657756 CI39326265311: six backend/static/security/PG/mobile jobs and frontend production build passed; browser reached new proposal375 workflow then failed clicking its TTN link because a foreground dialog intercepted it. Inspected synthetic log and actual Orders onSuccess / EntitySidePanel / Drawer / Modal source: fulfillment success selects SYN-1001, which mounts an order drawer below1024 containing the shipment-details section. The new scenario tried to act on the wizard behind that drawer.
- Fixture now targets the wizard by its actual dialog name and closes the foreground SYN-1001 drawer with its scoped header Close button. Escape was deliberately avoided because both mounted overlays register Escape handlers. No force click, event dispatch, page navigation shortcut, sleep, overlay removal, or source guard change. It then asserts exact existing shipment_id and conversation/order/shipment TTN URL identities, clicks normally, and retains manual draft / explicit replacement / no-analysis-or-send assertions.
- Added explicit DIRECT_TEST_SUITE=proposal to the existing fail-closed harness. Missing mode defaults to full; explicit full also runs every existing Direct/fulfillment/advertising/proposal scenario. Proposal mode runs the complete newly authored proposal scenarios with the same fixtures/assertions/failure capture/owned server, and result.json plus success output label the selected suite. Unknown mode rejects before Playwright load/server startup. Canonical CI invocation is unchanged.
- Root edge465 had an earlier existing initial375 card(a) visibility timeout while backend smoke ran concurrently. CI passed that stage; its old assertion and timeout remain unchanged pending root's quiet-host canonical rerun. Root native backend image/build and disposable database smoke passed. No application defect established by that isolated old-stage failure.
- Checks: Node22 --check on both changed browser modules and git diff --check passed. DIRECT_TEST_SUITE=invalid node frontend/scripts/direct-workspace-browser.mjs exited1 with exact 'Unknown DIRECT_TEST_SUITE: invalid' before runtime load/startup. Only scripts/report changed; backend/type/build/full browser were not rerun on Pi. Root owns isolated proposal-only and final complete runtime verification; no browser-pass claim.
