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
