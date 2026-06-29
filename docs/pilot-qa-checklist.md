# Sellora Pilot QA Checklist

Формат для кожної перевірки:

```text
[ ] Action:
Expected result:
Notes:
Severity if failed:
```

## Core access

[ ] Action: Login to staging/demo account.
Expected result: User lands in Sellora app without errors.
Notes:
Severity if failed:

[ ] Action: Switch language UA/EN.
Expected result: Labels change, backend enum values remain English in API-facing data.
Notes:
Severity if failed:

[ ] Action: Toggle dark/light theme.
Expected result: Text and cards remain readable.
Notes:
Severity if failed:

## Demo workspace

[ ] Action: Run `cd backend && python scripts_seed_demo.py` twice.
Expected result: Demo data exists and no duplicate DEMO records are created.
Notes:
Severity if failed:

[ ] Action: Open Dashboard in demo workspace.
Expected result: Demo badge appears, revenue/orders/top products/inventory alerts are meaningful, no NaN/Infinity.
Notes:
Severity if failed:

## Empty workspace onboarding

[ ] Action: Open Dashboard in a new/empty workspace.
Expected result: Setup checklist and useful first-run CTAs are visible.
Notes:
Severity if failed:

[ ] Action: Click each setup checklist CTA.
Expected result: Products, orders, advertising, integrations, import and analytics links navigate correctly.
Notes:
Severity if failed:

## Modules

[ ] Action: Open Products.
Expected result: Product list or action-oriented empty state appears.
Notes:
Severity if failed:

[ ] Action: Open Orders.
Expected result: Orders list or action-oriented empty state appears.
Notes:
Severity if failed:

[ ] Action: Open Inventory.
Expected result: Stock, low stock and out-of-stock states are understandable.
Notes:
Severity if failed:

[ ] Action: Open Customers and Leads.
Expected result: Lists or empty states explain next actions.
Notes:
Severity if failed:

[ ] Action: Open Shipments and Advertising.
Expected result: Lists/metrics or clear empty states appear.
Notes:
Severity if failed:

[ ] Action: Open Analytics.
Expected result: Reports load from real/demo data and no unavailable ratio shows NaN/Infinity.
Notes:
Severity if failed:

## Import Center

[ ] Action: Open `/settings/import`.
Expected result: Import helper explains dry-run, warnings, errors and duplicates.
Notes:
Severity if failed:

[ ] Action: Run product catalog dry-run with synthetic file.
Expected result: Counters, row-level warnings/errors and duplicate behavior are readable.
Notes:
Severity if failed:

## Mobile QA

[ ] Action: Check Dashboard, Orders, Products, Inventory, Analytics, Import Center at 375px, 390px, 430px and 768px.
Expected result: No body-level horizontal overflow; topbar, cards, tables and import actions remain usable.
Notes:
Severity if failed:

## Sprint 2.8 feedback and release checks

[ ] Action: Open the Feedback form from the topbar.
Expected result: Category, optional rating, required message, current page and privacy hint are visible.
Notes:
Severity if failed:

[ ] Action: Submit feedback with an empty message.
Expected result: Submit is blocked or validation appears.
Notes:
Severity if failed:

[ ] Action: Submit valid feedback.
Expected result: Loading state appears, then localized success message appears.
Notes:
Severity if failed:

[ ] Action: Open `/settings/feedback` as owner/manager.
Expected result: Workspace-scoped feedback list appears without raw internal IDs in the primary UI.
Notes:
Severity if failed:

[ ] Action: Review known limitations and pilot release notes with the pilot user.
Expected result: User understands what is manual, what is not automated yet, and how to report problems safely.
Notes:
Severity if failed:

## Sprint 2.9 Pilot QA Addendum — Mobile polish and orders pagination

- [ ] Open the mobile sidebar at 375px.
Expected result: profile, language, theme and logout controls are compact; email is truncated and does not stretch the drawer.
Notes:
Severity if failed: Major

- [ ] Open the app topbar at 375px.
Expected result: topbar stays on one row; feedback/language/theme are available from the More menu.
Notes:
Severity if failed: Major

- [ ] Select “Власний період” / “Custom period” on Dashboard.
Expected result: date fields do not overflow and calendar icons are visible in dark and light themes.
Notes:
Severity if failed: Major

- [ ] Open the Feedback form on desktop and mobile.
Expected result: centered modal on desktop, bottom sheet on mobile, overlay visible, submit/cancel accessible.
Notes:
Severity if failed: Major

- [ ] Open “Звіти” from sidebar.
Expected result: route opens the Analytics reports page without duplicate or blank reports screens.
Notes:
Severity if failed: Major

- [ ] Open /orders with more than 5 orders.
Expected result: first page shows 5 orders, page sizes 5 / 15 / 30 work, search/filter/sort reset pagination to page 1.
Notes:
Severity if failed: Major

- [ ] Re-test Analytics detailed table pagination.
Expected result: /analytics shows 5 detailed rows by default, page sizes 5 / 15 / 30 work, and changing the local period resets pagination to page 1.
Notes:
Severity if failed: Major

- [ ] Confirm there is no global period selector in the shared topbar.
Expected result: Dashboard and Analytics still have local period selectors, but the shared header no longer duplicates this control.
Notes:
Severity if failed: Minor

## Sprint 3.0 — Nova Poshta pilot QA

- [ ] OWNER can save and validate Nova Poshta settings while the saved credential remains masked.
- [ ] MANAGER can create shipments and TTNs only when sender settings and shipment fields are complete.
- [ ] ANALYST cannot mutate Nova Poshta settings or shipments.
- [ ] City and warehouse searches show loading, empty, and safe error states without raw Nova Poshta payloads.
- [ ] Creating a shipment from order opens `/shipments?order_id=...` with the order selected.
- [ ] TTN/tracking number appears on shipment and order details after successful creation.
- [ ] Duplicate TTN creation is prevented or clearly warned.
- [ ] Shipment status sync failure shows a safe localized message.
- [ ] Creating a TTN does not automatically mark the order as completed.
- [ ] No credential, sender private value, customer private data, or real TTN is included in pilot notes/screenshots.

## Sprint 3.1 pilot QA — Shipment workflow

- [ ] Create shipment from a linked-customer order.
- [ ] Confirm shipment detail sections are understandable for a store manager.
- [ ] Copy TTN from shipment list/detail/order detail when a tracking number exists.
- [ ] Confirm missing customer, recipient, sender settings and duplicate TTN states use localized safe messages.
- [ ] Confirm Nova Poshta status sync is clear when unavailable.
- [ ] Confirm mobile shipment list/detail are usable at 375px / 390px / 430px.

## Sprint 3.2 pilot QA — Nova Poshta staging stabilization

- [ ] Pilot store understands that TTN creation may create real Nova Poshta-side records and must use a controlled test shipment.
- [ ] Credential and sender settings edge cases show localized safe messages.
- [ ] Missing customer, phone, city and warehouse states block TTN creation with clear next steps.
- [ ] Duplicate TTN and incomplete TTN response behavior is safe.
- [ ] Status sync unavailable state is understandable and does not expose raw Nova Poshta payloads.
- [ ] Audit/log review confirms no raw credentials or private shipment data are stored.

## Sprint 4.0 — Advertising and Meta Ads readiness

- [ ] Explain to pilot users that advertising currently supports manual entry/import and that Meta Ads automatic sync is future work.
- [ ] Import or enter a synthetic daily advertising metric and confirm it appears in `/advertising`, Dashboard and Analytics for the same period.
- [ ] Confirm campaign rows are understandable to a shop manager and show source/platform context without exposing technical IDs as primary UI.
- [ ] Confirm empty advertising states guide users to manual import rather than implying Meta Ads is connected.
- [ ] Confirm no real Meta access token, app secret, ad account ID, business ID, private customer data or real campaign export is used in QA artifacts.

## Sprint 4.0.1 — Advertising staging follow-up

- [ ] With staging credentials, open `/advertising` and verify manual/import source messaging, campaign source badges and zero-denominator display.
- [ ] Open `/settings/integrations` and verify Meta Ads is clearly marked as preparation/future sync only.
- [ ] Use synthetic advertising metrics only; do not import real ad account exports or real campaign/customer data into QA artifacts.
- [ ] Confirm Dashboard and Analytics advertising cards remain consistent with `/advertising` for the selected period.

## Sprint 4.1 Pilot Advertising QA

- [ ] Manual advertising import remains the first-class MVP path.
- [ ] Pilot stores can test with synthetic data before any real business export is considered.
- [ ] `/advertising` explains manual/import source and Meta Ads future work.
- [ ] ROAS, CPA, CPL, ROI, conversion rate, and cost per message follow `docs/advertising-metrics.md`.
- [ ] Campaign attribution is optional for leads/orders; missing campaign data must not block order creation.
- [ ] Workspace/RBAC expectations are preserved: frontend hiding is not treated as the only security control.

## Sprint 4.2 Advertising Pilot Readiness

- [ ] Pilot can find or receive the advertising import template.
- [ ] Pilot understands that the template starts with synthetic rows and should not contain tokens, account IDs, customer personal data, or real campaign exports in QA artifacts.
- [ ] Pilot can follow `docs/advertising-import-guide.md` to prepare the spreadsheet, run dry-run, fix row errors, and execute import.
- [ ] Pilot can use `docs/pilot-advertising-guide.md` to understand ROAS, CPA, CPL, ROI, and campaign comparison.
- [ ] Campaign attribution limitation is clear: leads/orders do not require campaign attribution, and Meta attribution remains future work.

## Sprint 4.3 Advertising Decision-Support Checks

- On `/advertising`, compare the same selected period across campaign comparison, Top Campaigns, and Campaigns Needing Attention.
- Confirm statuses map to understandable Ukrainian labels: Добре працює, Потрібно спостерігати, Потребує уваги, Недостатньо даних.
- Confirm insights do not recommend scaling when spend is missing or when campaign data is incomplete.
- Keep advertising import marked not pilot-ready until deployed staging QA is completed with synthetic CSV data.

## Sprint 4.3.1 Advertising Insights Pilot Checks

- Confirm campaigns without metrics remain visible as **Недостатньо даних** instead of disappearing from comparison.
- Confirm spend + leads + zero orders is **Потребує уваги**, not **Добре працює**.
- Confirm Top Campaigns excludes NO_DATA rows and Campaigns Needing Attention uses PROBLEM before WATCH.
- Confirm unavailable values use `—` and never `NaN`, `Infinity`, `undefined`, or raw `null`.
- Keep advertising import not pilot-ready until manual staging import QA passes with synthetic data.

## Sprint 4.3.2 Advertising Insights Pilot Validation Follow-up

- [ ] Confirm frontend typecheck and production build have passed in an approved dependency environment before pilot-facing Sprint 4.3 approval.
- [ ] Confirm `/advertising` browser QA with synthetic GOOD, PROBLEM, WATCH/high-CPA, and NO_DATA campaign scenarios has been completed without runtime, hydration, or missing-translation errors.
- [ ] Confirm mobile widths and dark/light themes remain readable for the insights panel, campaign cards, comparison table, decision badges, and metric explanations.
- [ ] Confirm advertising import remains not pilot-ready until deployed manual import staging QA is completed with synthetic CSV data.
