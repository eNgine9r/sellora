# Sellora MVP Readiness — Sprint 2.7

## Ready for guided pilot testing

| Area | Status | Notes |
| --- | --- | --- |
| Core CRM flows | Pilot-ready | Leads, customers and order flow are available for guided testing. |
| Orders | Pilot-ready | Multi-item orders, statuses, payments and historical imports are available. |
| Products | Pilot-ready | Products, variants, categories and catalog import are available. |
| Inventory | Pilot-ready | Stock, reserved/incoming/minimum quantities and low-stock states are visible. |
| Analytics | Pilot-ready | Dashboard and Analytics reports use real/demo aggregate data. |
| Advertising manual metrics | Pilot-ready | Manual/imported historical ad metrics support spend, revenue and ROAS review. |
| Import Center | Pilot-ready with guidance | Dry-run, mapping, validation, row issues and duplicate warnings are available. |
| Demo dataset | Pilot-ready | Synthetic DEMO seed is idempotent and safe for demos. |
| Nova Poshta settings | Needs real API validation | Settings and shipment scaffolding exist; real API credentials need staging verification. |
| Localization | Pilot-ready | Ukrainian is primary; English is secondary. |
| Mobile UX | Needs pilot QA | Mobile-safe patterns exist; pilot checklist covers 375px/390px/430px/768px. |

## Known limitations

- Instagram Direct API is not connected yet.
- Meta Ads API is not connected yet.
- Billing/subscription system is not implemented yet.
- Full self-serve production onboarding is not implemented yet.
- Nova Poshta TTN behavior may require final validation with real settings/API key.
- AI Direct parser and predictive analytics are out of scope for this MVP phase.

## Next planned features after pilot feedback

1. Improve onboarding based on first-store behavior.
2. Expand import presets for common spreadsheet formats.
3. Harden Nova Poshta real-credential workflows.
4. Prioritize Instagram/Meta automation based on pilot pain points.
5. Add billing only after value and pricing are validated.

## Sprint 2.8 pre-MVP feedback readiness

- In-app feedback is available from the topbar with category, optional rating, message, current page and privacy hint.
- Feedback records are workspace-scoped in backend storage; owners/managers can review them in `/settings/feedback` and owners can update status.
- Pre-MVP release checks, known limitations and pilot release notes are documented for controlled external pilots.

## Sprint 2.9 readiness update — Mobile and list polish

- **Mobile sidebar footer:** compact profile row, aligned language/theme controls and compact logout are ready for pilot QA.
- **Mobile topbar:** secondary actions are consolidated behind a More menu on mobile so the primary order action stays reachable at 375px.
- **Date range selector:** custom period date inputs are mobile-stacked and native calendar indicators are styled for light/dark visibility.
- **Feedback modal:** feedback now uses the standard overlay modal/bottom-sheet pattern and keeps submit/cancel controls visible.
- **Reports navigation:** `/reports` is a stable alias to the existing `/analytics` reports experience to avoid duplicate report pages.
- **Orders pagination:** `/orders` defaults to 5 rows per page, supports 5 / 15 / 30 page sizes, and resets to page 1 when search, filters or sorting change.
- **Responsive QA focus:** verify 375px / 390px / 430px / 768px for dashboard, orders, products, inventory, analytics/reports, settings, feedback and sidebar drawer before pilot release.

### Sprint 2.9 follow-up checklist

- **Feedback modal positioning:** rendered through a viewport-level overlay so it is not clipped by the topbar/sidebar and remains usable as a bottom sheet on mobile.
- **Mobile More menu:** uses fixed viewport positioning with outside-click close behavior to avoid clipping and z-index conflicts.
- **Analytics pagination:** detailed sales rows on `/analytics` use the shared 5 / 15 / 30 pagination controls and reset when the local period changes.
- **Global period selector removal:** shared topbar no longer shows the duplicated period selector; local selectors remain on Dashboard and Analytics.
- **Topbar alignment:** visible topbar actions keep consistent height/alignment while avoiding unnecessary width changes.
