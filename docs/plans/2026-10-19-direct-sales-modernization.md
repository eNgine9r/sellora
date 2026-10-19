# Sellora — Direct, delivery and CRM sales modernization
Date: 2026-10-19
Source of truth: latest user request; AGENTS.md; audit-context/order-flow.md, ui.md, ads.md.
Goal: reduce daily seller work from Direct to order/TTN and explain advertising results using actual CRM data.
Base: a1a5d5a56bab8a11c21a51918e00e2e45c65630c (same-origin API fix).

## Global Constraints
- Preserve server-enforced workspace isolation, RBAC, existing routes/enums and stock/order semantics.
- Use existing Next/React/Tailwind/i18n and FastAPI/service/repository patterns; no new dependencies or schema changes.
- No production customer writes, messages, TTNs, ad changes, fake purchase events or secret/PII artifacts. Test with synthetic fixtures.
- Ukrainian default; touched copy uses dictionaries. Honest loading/empty/error states and source labels.
- Desktop 1280/1440 and mobile 375/390 must be usable without document overflow; keyboard controls labelled.
- Keep migration worker/send flags disabled. Publish only reviewed passing code through existing authorized deployment.
- Scope task commits to listed area; do not commit other agents' audit files. No subagents from implementers.
- No frontend API requests to tailnet hosts: browser uses same-origin /api/v1.
- Existing historical data is not rewritten and analytics sources are never silently combined.

### Task 1: Usable Direct workspace on desktop and mobile
Read AGENTS and audit-context/ui.md and order-flow.md. Preserve existing customer extraction and fulfillment flows.
1. Put Direct in mobile primary navigation (replace Leads; Leads remains sidebar/more). Use existing localized labels/icons. Preserve five links plus profile.
2. Fix topbar Create order to /orders?create=1 and orders effect to open wizard without requiring customer_id; respect canManage and avoid reopening on every refetch. Existing customer/conversation deep links still work.
3. Functional conversation search by display name/username; filters All, Unread, Instagram, Order intent with counts or clear state. Filtering must not mutate selected thread or mark other conversations read; honest filtered empty state/reset.
4. Mobile/tablet: list screen -> selected thread screen -> labelled back-to-dialogs control. On desktop 1280 show list/thread; AI uses accessible open/close panel. At wider screens 1440+ support useful third column. No list stacked above a selected long thread. Bound message/list scrolling; composer reachable.
5. Drafts scoped by workspace+conversation. Selecting B must never carry A draft; no late AI suggestion or send success overwrites another thread's draft. Reset stale prepare/send output, surface prepare/send errors in UI, guard analyst actions. AI draft must not repopulate after user clears/types. HTTP success may carry FAILED_SAFE/RETRY_PENDING/RECONCILIATION_REQUIRED operation: clear only on actual operation COMPLETED (provider accepted, not delivery/read confirmation), show non-SENT state, block blind retry for ambiguous/reconciliation states according to existing backend contract. Handle callback variables rather than current selected thread.
6. Reduce unnecessary polling: conversations single query cache observers (do not invent push transport); messages only active selected thread, no hidden-tab polling; global summary slower when hidden (or no hidden polling), preserve focus refresh/new-message invalidation. Customer automation poll only where needed; do not disable history sync.
7. Improve touched conversation/thread copy and density with existing tokens. No fake Open/Unread chips or raw status/direction English in touched labels.
Verification: existing typecheck/lint/mobile static; add meaningful Playwright synthetic fixture test exercising search/filter, draft isolation including late response, mobile select/back, desktop widths, quick create. Reuse existing browser tooling; do not disable browser security. Record evidence. Do not write source-string-only tests for new behavior.

### Task 2: Honest order costs and TTN handoff
Read audit-context/order-flow.md and existing wizard, shipment details, Direct send contract.
1. Existing wizard sends unit_cost:0. Add non-negative per-line unit cost in existing payload; account for quantity in product cost and estimated profit review. Preserve values through step changes. Allow zero but explicitly show estimate/incomplete-cost cue if a line has no positive cost; no fabricated catalog cost (catalog has none). Respect existing sensitive-field permissions.
2. Review screen shows product costs, other costs, total and estimated profit distinctly. Keep price vs cost clear, localized validation.
3. Repair wizard result Open shipment to open existing shipment details via stable shipment ID/deep link. Shipments page must honor deep link after workspace reset and not open duplicate create form for an existing shipment.
4. Add deliberate 'Підготувати повідомлення з ТТН' action after successful TTN and in shipment details where a linked Direct conversation can be resolved through existing contract. Carry order+shipment identity (not client-provided arbitrary message) to Direct; load workspace-scoped order/shipment, verify relation/conversation and prefill localized draft with existing TTN. Never autosend. Use neutral wording: TTN created does not establish carrier handoff or delivery (do not say shipped/delivered merely because a number exists). Respect messaging-window/provider/send flags and never label delivered unless actual status. If reliable conversation resolution is unavailable, implement only wizard result (it already knows conversation) and keep shipment action absent with concern recorded.
5. Prevent TTN action overwriting an unsent draft silently: confirmation or insert action in Direct using existing confirmation UI.
Verification: meaningful behavior tests for cost*quantity, negative/invalid costs, review totals/payload, deep link, TTN draft versus manual draft, no send on navigation. Existing focused backend order tests if backend unchanged only report existing contract; no need fullsuite twice.

### Task 3: CRM-backed campaign sales alongside ad metrics
Read audit-context/ads.md. Implement additive read-only report using existing campaign_id on Order; do not replace existing AdMetric contracts.
1. Backend repository aggregates workspace-scoped nondeleted orders by campaign for UTC created_at dates inclusive selected period, avoiding order-item/metric join multiplication. Group only campaigns belonging to workspace, retain visible archived campaign history (status ARCHIVED with deleted_at null). Respect existing soft-delete rules: deleted/missing/foreign campaign links go to unattributed without dropping their nondeleted CRM orders or exposing hidden campaign names. Spend uses the existing visible nondeleted metric/campaign scope.
2. Explicit report semantics: all placed orders, active (NEW/CONFIRMED/SHIPPED/DELIVERED/COMPLETED excluding REFUNDED), cancelled, returned/refunded counts; fulfilled sales = DELIVERED/COMPLETED excluding refunded. Report fulfilled revenue from this set and PAID subset separately; COD does not prove collection. Operational placed/active revenue stays separately labelled. Unknown campaign not credited. Label this convention in localized UI and API schema docs.
3. Same-period campaign spend from existing nondeleted AdMetric and fulfilled CRM revenue support CRM period revenue/spend and cost per fulfilled order with null zero denominator. Clearly a period report, not causal/cohort attribution; campaign linkage may be manually assigned and must say so. Do not claim referral/ad_id automation or current live Meta Ads sync.
4. Return aggregate attribution coverage: placed order counts with/without valid campaign, unknown/unattributed amount/count, per campaign CRM counts/revenue/spend, existing metric-declared orders/revenue separately. Cancelled takes precedence over returned/refunded for disjoint lifecycle buckets. No customer PII. Keep sensitive profit hidden by role; do not add new profit metrics.
5. Thin authenticated route with existing advertising read RBAC. Add frontend service/types, compact CRM sales section on Advertising using current date range; mobile cards + desktop table. Surface loading/error/empty state and next action to assign campaign in orders. Preserve current campaign metrics section clearly labelled 'Внесені рекламні метрики'. Collapse repeated methodology/readiness explanations into one expandable explanation; retain important disconnected/source warnings.
6. Actual order entry must allow campaign selection in wizard if missing, storing existing campaign_id; selected campaign persists through steps, no automatic guess. No provider mutations.
Verification: backend fixtures cover tenant isolation/RBAC, dates inclusive, deleted records, all lifecycle/payment outcomes, no double count from multiple items/metrics, zero spend/orders, CRM orders without metric and metrics without CRM orders, linked/unattributed. Frontend synthetic behavioral check date range, empty/error state, mobile/desktop and separate source labels. Relevant CI tests.

## Completion
Fresh CI checks, behavioral browser tests, task reviews + final scoped broad review. Deploy reviewed frontend and backend through existing setup, run read-only public auth/API/UI canary. Write concise audit dossier + next backlog (product extraction/catalog matching, Meta referral attribution/live connector activation, TTN auto-message approval) as proposals not completed features. No claim full live Instagram automation until Meta callback/worker cutover validated.
