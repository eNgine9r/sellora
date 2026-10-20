# Task 2 — honest order costs and TTN handoff

Status: IMPLEMENTED; isolated production build and synthetic browser execution pending root verification.

## Summary
- Existing fulfillment items retain editable non-negative unit_cost through steps and pass it in the existing payload. Review subtracts quantity × unit cost plus other costs; product/total-cost/profit aggregates retain the existing owner permission, and all managers see the incomplete-zero-cost cue. Empty, negative, nonfinite costs and nonfinite totals are rejected with dictionary copy.
- Wizard shipment navigation carries the stable shipment ID. Shipments loads the workspace-scoped detail after workspace reset; legacy order links first GET the existing shipment and create a form only when that GET confirms absence.
- Successful wizard TTN and uniquely linked shipment details offer identity-only Direct navigation. Direct reloads scoped order/shipment/customer-automation, checks IDs/workspace/order/customer/conversation relationships, carrier, actual shipment states and operation reconciliation state, then offers deliberate insertion. Existing text requires the shared confirmation dialog; navigation never calls prepare/send.
- Neutral Ukrainian/English copy describes a created shipping document, never carrier handoff or delivery. Existing messaging-window/provider/operation send guards remain authoritative.
- Direct drafts use existing session query cache keyed by user plus workspace/conversation ownership; revisions and old-callback guards survive the wizard route. Logout already clears the query cache. No PII draft is added to browser storage.
- Compact always-reachable thread header button scrolls to existing customer/order card. Handoff preview stays in the existing internal scroll pane, retaining composer bounds.
- Existing campaign selector and all Task 1 guards are preserved. No future product-proposal work, dependencies, API changes, schema changes, provider writes or live customer operations.

## Files changed
- Direct page; new Direct TTN draft component and TTN readiness/link helper.
- Fulfillment wizard; shipments page and shipment details.
- Existing order/shipment GET service wrappers and optional explicit workspace header on automation GET.
- Ukrainian/English dictionaries.
- Existing CI browser harness extended with synthetic fulfillment fixture/scenarios; existing CI already runs the harness and uploads its evidence.
- Root-authorized Task 2 plan clarification.

## Checks run
- Fresh final rerun on Node 22.23.2: npm run typecheck && npm run lint && npm run mobile:audit:static — exit 0 (14.70s). Typecheck/lint clean; mobile static inspected 29 routes, zero shared-overlay exceptions, PASS.
- node --check frontend/scripts/direct-workspace-browser.mjs
- node --check frontend/scripts/fulfillment-browser-fixture.mjs
- node --check frontend/scripts/fulfillment-browser-scenarios.mjs
  All syntax checks passed.
- git diff --check — passed.
- node frontend/scripts/orders-inventory-shipments-pilot-regression.mjs — 24 checks passed.
- node frontend/scripts/nova-poshta-real-validation-regression.mjs — 16/16 passed.
- node frontend/scripts/direct-app-shell-regression.mjs — 18 checks passed.

## Contract review and self-review
- Existing GET /orders/{id}, GET /shipments/{id}, GET /orders/{id}/shipment and Direct customer-automation remain workspace-scoped/RBAC-enforced backend contracts; no backend edits/tests rerun.
- Existing automation stages are PROSPECT_READY_FOR_ORDER before linking and CUSTOMER_READY once linked and complete; synthetic fixtures use those actual service states.
- TTN drafts accept CREATED/IN_TRANSIT/ARRIVED/DELIVERED Nova Poshta shipments with a number; reject DRAFT/RETURNED/CANCELLED, manual reconciliation, and non-COMPLETED operation state when present. Mere leftover number is insufficient.
- Confirmation component is keyed by workspace/conversation/order/shipment and unmounts on context changes; insertion uses the current per-thread setter/revision. Query data reloads independently of URL-provided text; no arbitrary message is accepted.
- Legacy deep-link side effects wait for fresh scoped GET completion, including a refetch after a workspace reset, to avoid opening a create form based on stale cached null.
- Sensitive aggregate costs/profit follow the existing order form's owner gate; item cost entry remains available to managers as in the existing order form.

## Pending / concerns
- Root owns isolated build/browser, CI, push and deployment. Browser scenarios are authored but have not yet run; selectors/fixtures require runtime verification before a completion claim.
- Added scenarios cover actual cost payload/review (3 × 40, other costs 20, profit 160 on revenue 300), invalid/negative/nonfinite/zero cost, step persistence, result-to-existing shipment, legacy link/workspace reset, verified TTN insert/manual draft confirmation, failed/mismatched relationship, 375/390/1440 composer bounds, and late send callback across route remount.
- No backend provider activation or real send/TTN was exercised. TTN actions stay absent if conversation relation is absent/ambiguous. Backend remains the send policy authority.

## Review/runtime correction — round 1
- Root's isolated production build of exact 60129d557f1a2868a07490768c35ebfc128f5224 passed. Its synthetic browser run failed before cost selection at fulfillment-browser-scenarios.mjs:20: exact getByLabel("Товар і варіант") could not match the implicit label containing option/stock text. Replaced with an asserted combobox role and stable localized name prefix; browser rerun is pending root.
- Review I1 confirmed: a React handoff element stays truthy even when its child returns null, so every timeline count change previously scrolled top. Replaced this persistent mode with one-time scroll intent per full handoff identity after initial timeline loading. Later count changes resume newest-message scrolling. The remembered identity/count also makes repeated identical effects idempotent. No draft setters, send policy or operation/revision ownership changed.
- Added dynamic inbound timeline rows and optional provider-accepted sent rows to the existing fail-closed fixture. New scenarios assert actual viewport/bottom scrolling after TTN insertion, then an explicit synthetic manager send; failed-link contexts also receive a new inbound and must scroll to it. Navigation/insertion still explicitly asserts zero prepare/send before that deliberate send.
- Fresh focused checks before the final identity/count idempotence adjustment: npm run typecheck && npm run lint && npm run mobile:audit:static — exit 0 (13.86s); 29 routes, zero overlay exceptions, PASS. Final rerun follows in the next record.
- node --check on the changed browser harness/scenario and git diff --check passed. The authored dynamic browser regression has not yet executed; no browser-pass claim.

- Final identity/count-idempotence version: npm run typecheck && npm run lint — exit 0 (13.97s). Repeated node --check for both changed browser modules and git diff --check — passed.

## Review/runtime correction — round 2
- Root's isolated build of ce36fa5 passed. The browser reached 18 completed check groups, including cost quantity/payload/review, TTN/manual draft confirmation, new inbound/sent scroll, narrow viewport, and legacy link/workspace reset. It then failed only on an ambiguous close-button selector in the final late-callback/remount scenario: both backdrop and header close matched. Switched that scenario to the existing supported Escape close and assert the dialog disappears. This is partial browser evidence, not a full-suite pass.
- Re-review I2 confirmed and fixed: when conversation or pane disappears (mobile Back), clear the remembered scroll context. Reopening A with its same cached message count initializes the new DOM pane at its newest message again. Added A → Back → A assertions at 375 and 390 for unchanged timeline count, actual newest-message viewport and bottom position, retaining draft ownership checks.
- Root's synthetic 375 screenshot showed the refresh-profile button squeezing identity to one letter and a US-formatted expiry date. Profile layout now has a bounded avatar/name grid and a separate action row; identity can wrap. Expiry uses the active Ukrainian/English locale with day/month/full year and hour/minute. Node formatter check outputs 19.10.2099, 23:00 for uk-UA. No global date/currency changes.
- Added narrow profile name-width/button-nonoverlap/date checks and synthetic profile screenshots at the existing 375/390/1440 TTN scenarios. The original composer-bound checks remain.
- Failure catch now captures a viewport PNG plus bounded URL/recent API/DOM text/error context from still-open pages created only by the fail-closed synthetic fixture, preserving original failure. No real-session or external page capture.
- Fresh focused typecheck/lint/mobile-static run: exit 0 (13.77s), 29 routes, zero overlay exceptions, PASS. Syntax checks on both changed browser modules and git diff --check passed. Final typecheck/lint after the explicit four-digit-year formatter is recorded below.
- New exact-SHA build/browser and scoped re-review remain root-owned and pending. Root-owned roadmap documentation is excluded from this correction commit.

- Final round-2 source: npm run typecheck && npm run lint — exit 0 (13.75s). No production build or browser execution on the live Pi.

## Runtime geometry correction — round 3 (systematic debugging)
- Applied obra-systematic-debugging: inspected exact synthetic failure screenshot/JSON/log, reproduced on root's existing isolated 66546fd production artifact with a temporary owned-port harness, instrumented bounded pane/child/footer geometry and scrollTo calls, then tested one resize-follow hypothesis before editing canonical source. No live data/provider calls or production build on the live Pi.
- Measured root cause on cached mobile reopen: initial smooth scroll used scrollHeight 2310 and clientHeight 233, clamping the destination to 2077. About 56ms later the existing extraction portal expanded CustomerAutomationCard from 149 to 278px (+129), making scrollHeight 2439 and actual bottom 2206. The old smooth animation still ended at 2077: final bottom gap 129px. Latest message bounds were y513–533 while pane bounds were y199–432. Profile height 205 and footer height 256 stayed unchanged; no API/page errors. Identity/count had not changed, so no second effect corrected geometry.
- Single-hypothesis demo on the same built artifact: observing actual child-flow resize and updating a latest-message scroll intent ended at scrollTop 2206 for height 2439/client 233 (gap 0). Latest message moved to y384–404, inside pane y199–432. This demonstrates the geometry cause; it is not a full canonical source/browser pass.
- Canonical source now initializes ordinary latest-message intent with auto scrolling and observes both the real inner content wrapper and the pane with ResizeObserver. Layout changes from the existing portal or composer keep latest intent at the actual bottom. Initial handoff intent stays top; explicit header/history input turns off resize-follow. Observer disconnects on conversation/pane cleanup. Existing one-time handoff/new-message/revision/send ownership guards remain.
- Added a deterministic behavior scenario holding the actual automation GET, loading the unchanged timeline first, then releasing the existing customer card and extraction portal. It asserts latest stays visible/bottom without a count change; a second case explicitly chooses header top before release and asserts no jump. Existing same-cached-thread Back/reopen and post-insert/new-inbound/explicit-send regressions remain strict.
- Failure context now includes bounded numeric pane geometry. Temporary diagnostic harness files were removed from the edge clone; tracked edge source is unchanged (git status only preexisting artifacts). Owned diagnostic servers exited through the harness cleanup. Numeric diagnostic evidence remains in this report; synthetic traces are under /tmp/sellora-pane-debug.json and /tmp/sellora-pane-observer.json on the isolated device.
- Fresh final npm run typecheck && npm run lint && npm run mobile:audit:static — exit 0 (13.99s), 29 routes, zero overlay exceptions, PASS. Both changed browser modules pass node --check; git diff --check passed.
- Root owns the new exact-SHA production build/full synthetic suite/re-review/CI. No canonical browser-pass claim until that run; no further unrelated edits or full CI retries by implementer.
