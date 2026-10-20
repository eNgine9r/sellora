# Final browser gate correction — 2026-10-20

## Summary / root cause
Base: 65dc8f201566694b2d2154c2ec520946e73c4460, branch codex/2026-10-19-direct-sales-workspace. The defect is browser-test instrumentation, not application navigation or API behavior.
The late-order workspace scenario uses a 375px viewport but clicked `.account-profile-trigger`. `frontend/src/components/profile-menu.tsx` explicitly renders that desktop control `hidden ... md:flex`. The visible mobile control is in `.mobile-bottom-nav`, accessible name `Профіль`, and opens the existing workspace switcher in MobileMoreSheet.
The hidden-control click never switched workspace or released the held response. The ordinary authenticatedFetch 20,000ms timeout aborted that request; the already-created response waiter then rejected at 30,000ms, masking the pending UI action. No response-owner guard caused the failure.

## Exact evidence and red/green experiment
- Inspected CI 39329362958, job 118323353184 using `gh run view 39329362958 --json jobs` and `gh api repos/eNgine9r/sellora/actions/jobs/118323353184/logs`. Production build/typecheck/lint passed; the browser job failed at original scenario line294 with `page.waitForResponse: Timeout 30000ms exceeded`.
- Fresh unchanged baseline: `PATH=/home/nexolab/.nvm/versions/node/v22.23.1/bin:$PATH PLAYWRIGHT_RUNTIME_PACKAGE=/home/nexolab/commander-workspaces/sellora-browser-runtime/package.json DIRECT_TEST_SUITE=proposal node frontend/scripts/direct-workspace-browser.mjs` redirected to `/home/nexolab/commander-workspaces/sellora-final-red.log`. Exit1,78.59s, same line294 timeout.
- Added temporary request/response/requestfailed timing instrumentation only; same command to `sellora-final-diagnostic.log` exited1,67.18s. Create branch: held ready572ms, release753ms, original-workspace200757ms. Workspace branch: held ready546ms; no second-workspace GET and no release; original-workspace request failed20306ms with `net::ERR_ABORTED`, then response waiter timed out.
- Single-variable experiment changed only the hidden desktop locator to visible mobile profile entry plus visibility assertion (original waiter position retained). Same command to `sellora-final-diagnostic-green.log`: exit0,38.24s, `Direct synthetic browser gate passed (suite=proposal, 10 scenarios).` Workspace evidence: original GET302ms; held ready525ms; second-workspace GET716ms; scoped404726ms; release740ms; original-workspace200743ms. Existing absence-of-old-order/dialog assertions passed after settlement. No timeout extension, synthetic response shortcut or forced click.
- Temporary diagnostics were removed after proof. Only the bounded final changes below remain.

## Files changed
- `frontend/scripts/order-proposal-browser-scenarios.mjs`: use the visible mobile bottom-nav profile button with localized exact role/name and assert visibility. Register the unchanged old-response URL/workspace/status predicate immediately before explicit fixture release, after UI actions, so an earlier UI-action failure cannot be masked by an unawaited response timeout. The response remains held until after all ownership-changing UI assertions; it cannot race ahead of waiter registration.
- `.superpowers/sdd/2026-10-19-direct-sales-modernization/final-browser-fix-report.md`: this evidence report.

## Self-review / preserved contracts
- Verified all102 pre-existing assertion lines remain verbatim (multiset comparison against HEAD); the only added assertion is profile visibility. Existing create/workspace/scoped404/late200 behavior, manual draft/cost/price/campaign, review consent, variant ownership and viewport375/390/1280/1440 coverage are unchanged.
- No application, backend, API/schema, auth, query owner, response ID/workspace, filter-independent lookup, timeout, fixture payload, dependency or CI changes. No skipped scenario or widened timeout.
- Node22 syntax check and `git diff --check` passed. Existing production build65dc8f2 is reused because only an .mjs scenario changed; no application build/type/lint rerun is required by the brief.
- Browser requests use the unchanged fail-closed same-origin synthetic harness and owned temporary server. No live customer/provider writes, send/TTN writes, production secrets, push or deployment.
- Untracked root artifacts and brief are excluded from commit. Baseline evidence copied to `artifacts/final-browser-baseline-20261020`; normal harness output remains `artifacts/direct-modernization`. The two orphan temporary Next servers from failed/unhandled red runs were verified against their owned ports37873/44095 and stopped; unrelated Next PID2369/port3100 was untouched.

## Final verification
- Final-source proposal: the command above redirected to `/home/nexolab/commander-workspaces/sellora-final-proposal.log`; exit0,36.62s; `Direct synthetic browser gate passed (suite=proposal, 10 scenarios).` Preserved result at `artifacts/final-browser-proposal-20261020/result.json` independently checked syntheticOnly=true, suite=proposal,10 checks,failures=[].
- Final-source default/full: `env -u DIRECT_TEST_SUITE PATH=/home/nexolab/.nvm/versions/node/v22.23.1/bin:$PATH PLAYWRIGHT_RUNTIME_PACKAGE=/home/nexolab/commander-workspaces/sellora-browser-runtime/package.json node frontend/scripts/direct-workspace-browser.mjs` redirected to `/home/nexolab/commander-workspaces/sellora-final-full.log`; exit0,100.41s; `Direct synthetic browser gate passed (suite=full, 35 scenarios).` Default mode was intentionally used, not a reduced run.
- Final Node22 syntax check and git diff whitespace check passed. Production source/build remains65dc8f2; both final gates used the unchanged build and final scenario source.
- Status: DONE for this bounded correction. No known remaining issue in scope. Independent review and exact-head CI/publication remain root-owned; no push/deploy was performed.
