# Task 3 — Meta Ads frontend and integration browser gates

## Summary

Implemented the runtime-aware Meta Ads setup flow against Task 2's actual routes/contracts. The UI does not invent a connected state or activate live integration flags. OWNER actions are scoped to the initiating workspace; account selection is explicit; sync imports only provider delivery data; local CRM fields remain editable.

Branch: `codex/2026-10-20-integrations-onboarding`. Assigned base: `cb67b0e1ce356c711bfdb08ae01eb32a2a863dc5`. All work and checks used Remote Desktop Commander on btc-radar in the assigned worktree. No backend implementation edits, deployment, push, migration, provider credential probe, campaign/budget write, order/message/TTN operation, token rotation, or Instagram callback change.

## Implementation and review surface

- Replaced the coming-soon card with backend readiness/blockers, localized configuration help, owner-only connect/reconnect, last error/sync, account name/currency/timezone picker, empty/error/retry states, and confirmed disconnect. Expired/reconnect-needed connections can also be disconnected.
- Manual date range is limited to 91 inclusive days, uses the provider account timezone, prevents duplicate submissions, and handles manual-spend conflict, currency mismatch, rate limit, token/permission expiry, network/provider failures without suggesting currency changes.
- Callback bootstrap is gated to the exact Ads callback pathname. It captures code/state in window memory and removes query values before authentication restoration. It preserves history.state. The callback consumes/deletes that capture in an effect/ref flow. No provider code/token is persisted. Pending actor/workspace/state/expiry/phase metadata alone uses sessionStorage.
- Callback intent is actor/workspace bound, validates through authenticated backend POST, shares one in-flight exchange during StrictMode, recovers completed/repeated visits through backend status, and clears invalid/denied/expired/session-mismatched intent. Inactive handlers do not clear current intent; state-matching cleanup prevents an old completion from overwriting/clearing a newer reconnect.
- Ads callback HTTP responses use no-referrer/no-store. The browser verifies policy and immediate URL cleanup while cookie refresh is deliberately held. Callback API requests have no Referer header.
- Shared API change: callers with an explicit X-Workspace-ID fail with safe 409 workspace_changed if current workspace differs at initial dispatch or after 401 refresh. Existing callers without explicit scope keep their behavior. Ads and NP services attach their originating workspace explicitly.
- Shared auth change: ephemeral actor ID for cookie sessions, existing-user fallback for legacy initialization, and Ads intent/capture cleanup on logout/session clear, actor change and workspace switch. Cookie-session tokens/user data are not newly persisted.
- NP feedback is keyed to actor/workspace and checked again before setting messages. The integration content remounts at the workspace/actor boundary.
- Existing metric editor consumes source_type/provider_controlled_fields. The five Meta delivery/date fields are disabled with a source explanation. Local reach/leads/orders/revenue/net_profit remain editable; 409 provider_metric_read_only is localized. A Meta-sourced zero is not displayed as verified reach.
- Existing Direct gate is retained. Its fixture adds an explicitly disabled Meta status endpoint; source-copy assertions now describe manual/CSV plus runtime Meta sync rather than the removed coming-soon statement.
- NP and Ads production-browser runners share owned localhost server startup/cleanup, isolated Playwright package resolution, portable bundled Chromium default, optional explicit executable, and synthetic evidence outputs. INTEGRATIONS_TEST_BASE_URL supports independently authorized published-bundle checks with all APIs still intercepted. CI installs its existing isolated Playwright package; no dependency/lockfile changes.
- CI runs the existing Direct gate plus NP/Ads gates and both new intent/workspace regressions, then uploads synthetic screenshots/results.

## Changed files

- `.github/workflows/ci.yml`
- `.superpowers/sdd/sellora-integrations-onboarding-20261020/task-3-report.md`
- `frontend/next.config.ts`
- `frontend/scripts/advertising-browser-scenarios.mjs`
- `frontend/scripts/advertising-integration-foundation-regression.mjs`
- `frontend/scripts/direct-workspace-browser.mjs`
- `frontend/scripts/integrations-browser-runtime.mjs`
- `frontend/scripts/integrations-workspace-retry-regression.mjs`
- `frontend/scripts/meta-ads-intent-regression.mjs`
- `frontend/scripts/meta-ads-onboarding-browser.mjs`
- `frontend/scripts/nova-poshta-onboarding-browser-fixture.mjs`
- `frontend/scripts/nova-poshta-onboarding-browser.mjs`
- `frontend/src/app/advertising/page.tsx`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/settings/integrations/meta-ads/callback/page.tsx`
- `frontend/src/app/settings/integrations/page.tsx`
- `frontend/src/components/edit-record-dialog.tsx`
- `frontend/src/features/advertising/components/ad-metric-table.tsx`
- `frontend/src/features/integrations/components/meta-ads-readiness-card.tsx`
- `frontend/src/features/integrations/lib/meta-ads-intent.ts`
- `frontend/src/i18n/messages/en.json`
- `frontend/src/i18n/messages/uk.json`
- `frontend/src/services/api.ts`
- `frontend/src/services/auth.service.ts`
- `frontend/src/services/integrations.ts`
- `frontend/src/services/meta-ads.ts`
- `frontend/src/types/advertising.ts`
- `frontend/src/types/meta-ads.ts`

Root-owned `docs/plans/sellora-integrations-release-20261020.md` is excluded. Artifacts contain synthetic evidence and are excluded from the task implementation commit.

## Checks run

Final full frontend command, from frontend/:

```sh
npm run typecheck && npm run lint && NEXT_TELEMETRY_DISABLED=1 NEXT_PUBLIC_COOKIE_SESSION_AUTH_ENABLED=true npm run build
```

Result: exit 0; Next 15.5.19 compiled and generated all 33 routes. Latest additional npm run lint and npm run typecheck after the fixture authentication-precondition fix also exited 0.

Final production browser results on that build: Ads 15 scenarios passed; NP 1366/390 both passed; preserved Direct full 40 scenarios passed. All runners closed their browser/server. Ads verifies callback Cache-Control contains no-store and Referrer-Policy is no-referrer, query is already empty while cookie refresh is held, and captured window parameters are deleted after consumption.

The final negative fixture was corrected to wait for authenticated OWNER connect readiness before manually seeding callback intent. Creating intent while the first page was still bootstrapping authentication could race navigation/abort cleanup; that is not a real OAuth-start precondition. Focused denial reproduction passed, and the complete 15-scenario production suite then passed with the readiness precondition. No product security/tenant check was weakened.

Effective production browser commands (from repository root):

```sh
PLAYWRIGHT_RUNTIME_PACKAGE=/home/btcradar/nexolab711-work/package.json PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium node frontend/scripts/meta-ads-onboarding-browser.mjs
PLAYWRIGHT_RUNTIME_PACKAGE=/home/btcradar/nexolab711-work/package.json PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium node frontend/scripts/nova-poshta-onboarding-browser.mjs
NEXT_TELEMETRY_DISABLED=1 PLAYWRIGHT_RUNTIME_PACKAGE=/home/btcradar/nexolab711-work/package.json PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium node frontend/scripts/direct-workspace-browser.mjs
```

Focused real Next development/StrictMode command:

```sh
NEXT_PUBLIC_API_BASE_URL=/api/v1 NEXT_PUBLIC_COOKIE_SESSION_AUTH_ENABLED=true INTEGRATIONS_TEST_DEV=1 META_ADS_TEST_SUITE=callback PLAYWRIGHT_RUNTIME_PACKAGE=/home/btcradar/nexolab711-work/package.json PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium node frontend/scripts/meta-ads-onboarding-browser.mjs
```

Result: 1 scenario passed. This exercises the actual React effect, held authentication, query scrub, one callback POST, reload recovery, and no automatic account selection. The first real StrictMode run reproduced a meaningful bug: initial callback POST succeeded once, but a cleaned-up effect cleared the completed intent, causing reload recovery to report invalid state. Fixed by making inactive handlers return without consuming/clearing current intent and making attempt cleanup/save conditional on the matching state. Re-ran successfully after both that fix and the startup privacy bootstrap. Failure-before-fix PNG is retained separately.

New VM regressions pass:
- `node frontend/scripts/meta-ads-intent-regression.mjs`: shared pending exchange, status recovery, disconnected recovery rejection, actor/workspace binding, code privacy, and stale old completion/cleanup preserving a newer reconnect.
- `node frontend/scripts/integrations-workspace-retry-regression.mjs`: actual shared API module, both Ads and NP 401→held refresh→workspace switch; exactly one initial fetch, no retry to the new tenant; stale initial dispatch rejected before fetch.

Scoped existing static checks pass:
- advertising-attribution-mvp (9), advertising-freeze-handoff (32)
- nova-poshta-real-validation (16), meta-instagram (23), direct-app-shell (18)
- import-center-pilot (17), orders-inventory-shipments-pilot (24)

## Browser scenarios

Ads production suite: 15 named scenarios:
1. 1366 and 390: synthetic HttpOnly session, connect navigation intercepted before network, callback query scrub before held auth release, no code/access token persistence, one callback POST, reload recovery with no second POST, explicit unselected account picker, disabled currency-mismatched account, account selection, invalid>91-day range, successful sync and same-range repeat.
2. Both widths: manual_spend_conflict, currency_mismatch, RATE_LIMITED, TOKEN_EXPIRED, NETWORK_ERROR copy; late sync success stays in its originating workspace;401 refresh after workspace switch makes no new-workspace mutation; confirmed disconnect; document overflow and per-control containment/hit testing.
3. Configuration blocked; no accounts; status load error; denial; expired intent; actor mismatch; workspace mismatch; callback backend error; logout intent clear; reconnect/expired disconnect; ANALYST; MANAGER.
4. Provider metric editor: date/spend/impressions/clicks/messages disabled; local CRM fields editable and saved; stale 409 explained; local reach remains editable.

NP production suite: 1366 and 390 retain Task1 onboarding coverage and add workspace lifecycle:
- saved password is cleared and not browser-persisted; named sender/contact/city/warehouse selection; dependent clearing; blank-key payload preservation; synthetic verification; writes remain off; failed lookup/retry; populated control bounds/hit tests.
- Verification response held across workspace switch does not show old success/verification in the new workspace.401 followed by held cookie refresh does not retry the NP action in the new tenant. Fixture settings/directories are isolated by workspace.

All API routes are synthetic. Unknown operations reject; external browser traffic aborts except the intentionally intercepted synthetic OAuth navigation, which receives a blank synthetic document without contacting Meta. No test probes a real provider or performs a real data mutation.

## Evidence and visual review

Evidence root: `artifacts/integrations-onboarding/` under the assigned repository.

- `meta-ads/connected-1366.png`, `meta-ads/connected-390.png`
- `meta-ads/metric-editor.png`, `meta-ads/result.json`
- `nova-poshta/populated-1366.png`, `nova-poshta/populated-390.png`
- `nova-poshta/onboarding-1366.png`, `nova-poshta/onboarding-390.png`, `nova-poshta/result.json`
- `meta-ads-strictmode/failure-before-fix.png`, `meta-ads-strictmode/result.json`
- Existing Direct evidence remains in `artifacts/direct-modernization/`.

Control verification scrolls each input/select/button/link into view, checks its painted rectangles stay inside the card, and hit-tests the center against actual elements. This catches occlusion beyond page overflow. Mobile card screenshots can include the fixed app navigation while capturing a tall card; the interaction checks verify each control remains reachable by scrolling.

Visually inspected populated Meta card screenshots at 1366/390 and the provider metric editor. Labels, account metadata, two-column desktop date controls, stacked mobile date controls, error copy and disabled-vs-local metric fields are readable. No control clipping was observed; automated containment/hit tests also passed.

## Archival static failures reproduced at assigned base

A read-only `git archive cb67b0e1ce356c711bfdb08ae01eb32a2a863dc5` was extracted to a temporary directory (regular files/directories only; repository symlinks excluded), and the original scripts were run there with Node. No branch switch/reset or dirty checkout mutation was used. All five return exit 1 at BASE and current for the same archival assertions:

| Script | Same failure at BASE/current |
| --- | --- |
| advertising-staging-pilot-readiness-regression.mjs | optional attribution and Meta future-work markers remain |
| advertising-integration-foundation-regression.mjs | docs/mvp-readiness.md missing Sprint 4.0 readiness — Advertising integration foundation |
| advertising-insights-decision-support-regression.mjs | docs/mvp-readiness.md missing Sprint 4.3 |
| advertising-reporting-consolidation-regression.mjs | Sprint 4.4 remains conditional until runtime/browser QA |
| advertising-import-attribution-reporting-regression.mjs | dashboard/analytics consistency documentation; Meta API future-work marker |

The foundation script's deliberately replaced coming-soon-card markers were reconciled to runtime readiness, can_connect/can_sync and explicit selection. Its token/secret fixture scan and remaining checks remain intact. The new real-browser/API regressions supply behavior backstops. No archival security/tenant check was removed or weakened, and unrelated historical documentation was not rewritten to manufacture a pass.

## Self-review and remaining limits

Reviewed the edited React components using the React best-practices skill and the final verification evidence using verification-before-completion. Checked actual Task 2 response/error/source ownership contracts, OWNER controls, explicit scope on retry, pending feedback ownership, callback replay/StrictMode cleanup, no-referrer/no-store, input accessibility, mobile geometry, and synthetic-only provider boundaries.

No live activation is claimed. Ads remains dependent on separately configured/enabled runtime gates, a reviewed Meta application, granted permissions, real owner consent and a compatible explicitly selected account. The browser mocks validate frontend behavior, not live OAuth/provider correctness. Upstream ingress/access-log query suppression must still be validated before activation: browser cleanup cannot erase the original HTTP callback request already received by hosting infrastructure.

The five archival static failures above are existing debt, proven at the assigned base. Independent controller review, final release/CI evaluation and any authorized activation remain controller-owned.


## Review fix round 1/5 — I1 and M1

Fix base: `de528f7716045567abf4b55506a66ab3346194cc`.

### I1 — distinguish stale incoming arrival from a matched attempt failure

Reproduced the review finding with the actual transpiled callback page and actual intent module under synthetic React/auth/window/provider stubs. The newly added assertion failed before the fix: expected stored state `pending-B`, received undefined after stale A arrived. There were no additional callback POSTs. This is an effect/control-flow VM regression, complemented by real Next browser checks below; it is not a substitute for React StrictMode verification.

The callback page now rejects mismatched or missing incoming state for a pending attempt before any cleanup, and its generic promise catch only presents invalid_state. The intent module validates incoming association before looking up an in-flight promise or consuming metadata. Matching expired/invalid-code and provider-failed attempts remain cleared by the helper. Callback denial/auth rejection clears only an incoming matching attempt. A denial without state is shown as cancellation while preserving an unidentified pending B; matching denial still clears its own attempt. Explicit logout/session/workspace cleanup in auth.service.ts is unchanged.

The regression now proves all of:
- A arrives after B is stored: B remains pending, invalid-state UI, zero additional callback POSTs.
- Missing incoming state, with or without a code: B remains pending.
- Unassociated/state-free denial: B remains pending.
- B subsequently completes exactly once, including a second effect invocation and a stale A arriving while B is in flight.
- Query-free completed B recovers through status, without another POST.
- Matching expired and matching denied attempts clear their own metadata.
- The original late-A-completion-after-B regression is retained and passes.

### M1 — advertising wording

Updated Ukrainian provider_metric_read_only to: “Рекламні показники та дату контролює Meta Ads. Оновіть метрики й редагуйте лише локальні поля CRM.” Updated the existing browser expectation to the same advertising wording.

### Files changed by this fix

- frontend/src/app/settings/integrations/meta-ads/callback/page.tsx
- frontend/src/features/integrations/lib/meta-ads-intent.ts
- frontend/src/i18n/messages/uk.json
- frontend/scripts/meta-ads-intent-regression.mjs
- frontend/scripts/meta-ads-onboarding-browser.mjs
- .superpowers/sdd/sellora-integrations-onboarding-20261020/task-3-report.md

### Exact covering checks and results

All commands used Remote Desktop Commander on btc-radar in the assigned worktree.

```sh
node frontend/scripts/meta-ads-intent-regression.mjs
```

Red: AssertionError, “actual page must preserve B when older A arrives”; actual undefined, expected pending-B. Green after the fix: exit 0, both “Meta Ads intent regression passed” and “Actual callback component + intent regression passed: stale/missing-state arrival preserves B; B completes once; in-flight stale arrival rejected; sanitized recovery succeeds.”

```sh
NEXT_PUBLIC_API_BASE_URL=/api/v1 NEXT_PUBLIC_COOKIE_SESSION_AUTH_ENABLED=true INTEGRATIONS_TEST_DEV=1 META_ADS_TEST_SUITE=callback PLAYWRIGHT_RUNTIME_PACKAGE=/home/btcradar/nexolab711-work/package.json PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium node frontend/scripts/meta-ads-onboarding-browser.mjs
```

Real Next development/StrictMode: exit 0; “Meta Ads synthetic gate passed: 2 scenarios” (49.60s). Includes original held-auth query scrub/one POST/reload recovery plus stale-A/missing-state/unassociated-denial arrivals preserving B, then B completion once and reload recovery.

From frontend/:
```sh
npm run typecheck && npm run lint && NEXT_TELEMETRY_DISABLED=1 NEXT_PUBLIC_COOKIE_SESSION_AUTH_ENABLED=true npm run build
```

Exit 0 (67.87s). Next 15.5.19 compiled and generated all 33 routes; no typecheck/lint failures.

```sh
NEXT_TELEMETRY_DISABLED=1 META_ADS_TEST_SUITE=callback PLAYWRIGHT_RUNTIME_PACKAGE=/home/btcradar/nexolab711-work/package.json PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium node frontend/scripts/meta-ads-onboarding-browser.mjs
git diff --check
```

Production callback mode: exit 0; “Meta Ads synthetic gate passed: 2 scenarios” (15.44s). Diff check passed. Callback policy, immediate URL cleanup, window-capture deletion, no code persistence, no automatic account selection and the complementary per-attempt flow are exercised. Every API remains synthetic and external provider traffic is intercepted; no real provider/data action occurred.

The complete CI browser runner now defines 16 scenarios (the existing 15 plus the new attempt-isolation flow). Only the two covering callback scenarios were rerun locally for this fix, alongside the VM and frontend gates. NP/Direct were untouched and were not repeated, as requested; final CI remains controller-owned.

Fresh focused result manifests and attempt-isolation screenshots are under:
- artifacts/integrations-onboarding/meta-ads/result.json
- artifacts/integrations-onboarding/meta-ads/callback-attempt-isolation.png
- artifacts/integrations-onboarding/meta-ads-strictmode/result.json
- artifacts/integrations-onboarding/meta-ads-strictmode/callback-attempt-isolation.png

Both manifests record 2 checks and an empty failures array. Generated artifacts and the root-owned release-control document are excluded from this fix commit. Original de528f7 evidence was privately archived by the controller before this round. No new implementation concern identified; inherited archival-static/live-activation limits above remain unchanged.
