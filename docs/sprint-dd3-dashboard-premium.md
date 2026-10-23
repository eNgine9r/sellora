# Sellora — Dd.3 Dashboard premium UI

Status: feature PR #309 with READY preview. Release to main pending authenticated preview acceptance.

## Scope
- Preserve /dashboard, shared date range, API queries, RBAC, workspace isolation, analytics formulas and localization.
- Promote KPIs and revenue/profit chart; avoid misleading zeros while queries load.
- Compact actionable owner alerts; remove duplicate Dashboard notifications.
- Real-data-based lead/order/delivered stages; orders divided by leads is explicitly NOT an attributed conversion rate.
- Explain missing revenue and restricted data clearly.
- Preserve onboarding checklist through accessible details disclosure.
- Harmonize Dashboard-local cards, activities, light/dark theme and Ukrainian/English labels.

## Validation checklist
- [x] TypeScript typecheck and ESLint (no errors)
- [x] Next.js production build (initial commit)
- [x] Sprint 7C owner experience and Dd.3 premium static regression
- [x] Mobile UI static regression
- [x] Local Chromium visual QA: dark OWNER desktop 1440, tablet 768, mobile 390/375
- [x] Local Chromium mobile light theme 390
- [x] Local Chromium MANAGER role with restricted profit and chart
- [x] Local Chromium with orders but zero recorded revenue
- [x] Date selector switched from last30 to last7
- [x] Synthetic backend 503 error state: alert shown; KPI row hidden
- [ ] Real authenticated OWNER / MANAGER / ANALYST preview E2E (preview is protected by Vercel SSO)
- [ ] Public staging smoke test after controlled merge

## October 23, 2026 — visual QA evidence

Browsers: headless Chromium; source: local frontend, synthetic API responses injected in browser only. No real accounts created and no real shop data written. This verifies rendering and interaction but does not prove live backend data accuracy or auth behavior.

| Scenario | Width | Result |
| --- | ---: | --- |
| OWNER dark desktop | 1440px | PASS |
| OWNER dark tablet | 768px | PASS |
| OWNER dark mobile | 390px | PASS |
| OWNER dark compact mobile | 375px | PASS |
| OWNER light mobile | 390px | PASS |
| MANAGER restricted view | 1440px | PASS |
| OWNER no financial revenue | 1440px | PASS |
| Synthetic API error | 1440px | PASS |

All eight scenarios: zero page-width overflow. For the seven data-loaded scenarios, four KPI cards render, no KPI value overflows its element, and there are no fatal JavaScript page errors. Missing-revenue state shows an explanation. API-error state displays the failure and hides KPI instead of showing false zeros.

Issues found and fixed during QA:
- Major: mobile KPI amount and net-profit title truncated at 375/390px. Adaptive number size and wrapping fix applied.
- Minor: action links had list-item ARIA role overriding link semantics. Replaced with semantic list markup.
- Minor: inaccessible role could see unrelated chart legend, removed.

Remaining observations:
- Local Next.js development runtime reports a hydration attribute warning with theme bootstrap. Baseline / production reproduction needed; not attributed to this PR yet.
- Legacy dashboard-analytics-regression.mjs expects source markers that do not exist even on baseline main. Keep that unrelated test-maintenance debt separate.
- Preview SSO prevents real authenticated browser QA without explicit authorized login. Do not weaken project protection to bypass this.

## Release gate

Current status YELLOW. PR and preview can be reviewed. Do not merge to main or announce GREEN until role-based authenticated preview testing and public staging smoke test succeed.
