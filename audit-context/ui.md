# Sellora UI context map — 2026-10-19

Source-only audit. No authenticated browser visit, customer/provider calls, database changes, or runtime screenshots were made. Evidence describes the branch source; measured viewport behavior remains open.

## Existing product path

| Step | Existing UI | Evidence |
|---|---|---|
| Incoming Direct | Conversation list, unread badges, intent-first sorting, live-summary notifications | frontend/src/app/direct/page.tsx L425-L475; frontend/src/components/direct-live-provider.tsx L65-L81,L115-L157 |
| Customer | Prospect ensure, missing-field list, AI name/phone/address extraction and conflict review | direct/page.tsx L584-L659; components/direct-customer-extraction-panel.tsx L118-L205 |
| Order | Linked customer/conversation opens 3-step wizard | direct/page.tsx L638-L650; orders/page.tsx L212-L223,L340-L368 |
| Delivery | Nova Poshta city/warehouse lookup, readiness gates, order ± TTN, retry/reconciliation result | features/orders/components/order-fulfillment-wizard.tsx L211-L277,L279-L371 |
| Customer TTN | Result and shipment detail offer copy; result links back to Direct | order-fulfillment-wizard.tsx L289-L297; features/shipments/components/shipment-details.tsx L62; ttn-actions.tsx L6-L33 |
| Ads | Manual/import metrics, campaign association, period summary, trend, campaign results | advertising/page.tsx L64-L70,L99-L116; services/advertising.ts L9-L14 |

## Navigation and design facts

- Fifteen flat desktop links; Direct follows Leads rather than leading the operational flow (components/app-sidebar.tsx L9-L25).
- Mobile quick links are dashboard, leads, orders, products, finance plus profile; Direct is reachable via menu/more, absent from bottom links (app-shell.tsx L37-L43,L112-L123; mobile-more-sheet.tsx L40-L42).
- Mobile sidebar/footer and more sheet duplicate workspace/theme/language/logout; some are context-appropriate access points rather than duplicate business functions (app-shell.tsx L125-L138; mobile-more-sheet.tsx L26-L62).
- Topbar plus and more-sheet create CTA both call a function that navigates only to /orders; generic create=1 alone also does not open the wizard because customer_id is mandatory in the effect (app-topbar.tsx L42,L98-L105; orders/page.tsx L212-L217).
- Global search is only an input; no value/onChange/form action in its component (app-topbar.tsx L66-L69). Nothing found in this component establishes working search.
- /overview redirects to /dashboard and /reports redirects to /analytics; they are stable aliases, not duplicate page implementations (app/overview/page.tsx L1-L5; app/reports/page.tsx L1-L6).
- Existing semantic dual-theme CSS tokens and shared Button/Card/Field/Overlay foundations should be reused, not replaced (app/globals.css L5-L105; ui/primitives.tsx L12-L75; crm-workspace.tsx L26-L82).
- Existing order list has desktop table plus mobile cards and shared side-panel/drawer (features/orders/components/order-table.tsx L14-L16; crm-workspace.tsx L58-L82).

## Direct interaction facts

- Search has no controlled state or filtering handler; Open/Unread/Instagram/Test labels are spans, not filters (direct/page.tsx L447-L448).
- Every conversation is rendered; no pagination or bounded list viewport found in ConversationList (L449-L477).
- Under lg, conversation list and thread remain in the same grid flow; no list/detail back state exists (L259-L300). At lg the three-column template always includes a 320–380px AI column (L260,L301-L309).
- Reply draft is page-scoped, cleared only on workspace change; selecting another conversation updates only ID and URL (L63,L154-L160,L214-L217). The send mutation combines current selected conversation with this shared text (L119-L120).
- Prepare result is mutation data with no per-conversation association/reset found (L118,L297). Draft suggestion autopopulates whenever reply is empty (L170-L173).
- Query polling continues in background: live summary 2s, list 2s, messages 1.5s, automation 2s, extraction 1.5/4s, history 3s (direct-live-provider.tsx L65-L81; direct/page.tsx L70-L112; direct-customer-extraction-panel.tsx L78-L87). Shared list query keys let TanStack reuse its cache; do not claim every observer duplicates HTTP requests.
- Direct UI contains raw direction/status enums and mixed technical English (direct/page.tsx L444,L448,L469,L483,L561,L576,L624,L635,L680,L691,L698).
- Direct errors from send, prepare, analysis, and history mutations have no displayed error binding in the audited JSX (L114-L149,L219-L348); backend enforcement is outside this UI record.
- UI mount has POST effects (mark-read, profile refresh, potential customer ensure), so production navigation is not read-only (L175-L203).

## Advertising information hierarchy

The page repeats source, future Meta, attribution explanations and engineering readiness in multiple visible blocks before/around results (advertising/page.tsx L100,L104-L111,L116). Metrics are in three separate campaign/performance/daily tables (L112-L115). CampaignPerformanceTable is a 920px minimum table on all viewports, no mobile-card branch (features/advertising/components/campaign-performance-table.tsx L10-L18). Summary/performance/trend use selected dates; daily metrics fetch has no date arguments (advertising/page.tsx L64-L68; services/advertising.ts L9-L14). API source semantics must be confirmed before changing displayed totals.

## Proposed first coherent scope (for root implementation decision)

1. Center Direct in desktop/mobile navigation; group secondary links without deleting routes.
2. Make Direct search and actual status/channel/unread/intent filters work; distinguish empty inbox from filtered-empty.
3. Introduce mobile list → selected conversation → back; tablet/compact desktop use two columns with AI in a shared accessible drawer, wide desktop can show three columns.
4. Scope draft and prepare/send outcomes to conversation/workspace; keep typed drafts on safe thread switch and prevent suggestion overwrite.
5. Make global create order open the existing wizard. Keep warehouse verification, backend status/inventory rules, permission gates and explicit provider-write confirmation.
6. Clarify result navigation so an existing shipment opens rather than requesting another create flow; add safe TTN draft preparation only after linked-conversation/API capability review.
7. Consolidate ads education/readiness into one concise source/status disclosure and collapsible help, keep operational KPIs/results first; show mobile campaign cards with spend/orders/revenue/ROAS and unknown attribution explicitly.

## Verification strategy and remaining questions

- Use a bounded Playwright mock-API fixture with synthetic contacts/messages/products/orders only; intercept all /api/v1 requests, fail on unexpected requests, block provider hosts. Use normal browser security. Do not reuse old authenticated audit screenshots.
- Run 375/390/1280/1440 viewports in light/dark: no horizontal clipping, accessible primary actions, search/filter result correctness, mobile list/back, selecting thread, preserved draft ownership, generic create CTA, shipment result navigation, empty/error/loading states.
- Capture only synthetic-data screenshots; assert fixture traffic is isolated before capture. Existing scripts/mobile-ui-audit.mjs captures real authenticated data and launches with disabled security (L88-L100,L167,L182-L213), so it is not evidence for new UX.
- Existing mobile static regression checks source markers/strings and overlay inventory, not interaction correctness (scripts/mobile-ui-static-regression.mjs L10-L36,L60-L90). Keep applicable contracts but add behavioral checks for changed workflow.
- Backend costs snapshot, order transitions, TTN provider reconciliation/idempotency and send policy: delegated domain audit must establish these; no business-rule verdict from this UI audit.
- Can Meta referral/ad identifiers be surfaced to the order wizard? UI types inspected here do not expose them (types/direct.ts L6-L32). Need backend/schema audit before proposing attribution automation.
- Is selected Direct conversation shared safely with extraction portal? Provider derives selected conversation separately by URL polling every 500ms (direct-live-provider.tsx L90-L101,L179-L207); root should unify ownership if touching it.
