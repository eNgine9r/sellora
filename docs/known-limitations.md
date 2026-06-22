# Sellora Known Limitations for Pilot Users

Sellora is ready for guided MVP pilot testing, but the following limitations must be communicated honestly before users rely on it for daily operations.

## Not automated yet

- Instagram Direct API is not connected yet.
- Meta Ads API is not connected yet.
- Billing/subscriptions are not implemented yet.
- Advanced AI insights and predictive analytics are not implemented yet.
- AI Direct parser is not implemented yet.

## Integrations and imports

- Nova Poshta production TTN behavior may need final validation with real API settings.
- Some reports depend on imported or manually entered data.
- Import dry-run should be tested with copied/safe spreadsheet data before importing operational data.
- Feedback attachments/screenshots are not supported yet.

## Feedback/privacy boundaries

- Do not include passwords, API keys, tokens, private spreadsheets, raw customer lists, full authorization headers, or workspace IDs in feedback messages.
- Pilot feedback is workspace-scoped and intended for product triage, not for storing support evidence with sensitive data.

## Product scope

- Sellora currently focuses on CRM, products, inventory, orders, shipments, manual advertising metrics, imports and analytics.
- Full self-serve onboarding, billing, team administration and automated external API ingestion are planned after pilot validation.

## Sprint 3.0 Nova Poshta validation limitations

- Nova Poshta status sync is available as a manual action where a TTN exists, but automated background synchronization is not yet enabled.
- Nova Poshta TTN cancellation is not fully production-validated and should be treated as manual operational follow-up until a dedicated cancellation workflow is added.
- Sender counterparty and contact person refs may still need to be sourced from the shop’s Nova Poshta account; Sellora validates that they are present before TTN creation but does not yet browse all account sender entities.
- Production validation must use the staging checklist and a controlled test order because real TTN creation may create real records in the Nova Poshta account.

## Sprint 3.1 — Shipment / TTN limitations

- Printable or downloadable Nova Poshta TTN documents are not implemented yet. Pilot users should copy the TTN number from Sellora and use the Nova Poshta cabinet for printing.
- Delivery status sync depends on Nova Poshta API availability and requires an existing TTN; when unavailable, Sellora shows a safe localized message instead of raw third-party payloads.
- TTN creation does not automatically complete an order. Order status and shipment status are intentionally kept separate.

## Sprint 3.2 — Staging validation limitations

- Real Nova Poshta staging validation still requires a controlled shop-owned credential and may create records in the Nova Poshta account if TTN creation is executed.
- Automated tests continue to use mocked Nova Poshta clients; no real Nova Poshta API calls are made in CI/regression scripts.
- Printable/downloadable TTN documents remain out of scope; copy the TTN and use the Nova Poshta cabinet for document workflows.

## Sprint 3.2.1 — Remaining validation blockers

- Real Nova Poshta staging validation cannot be marked complete until a controlled shop-owned API key is provided and the manual checklist is executed in staging.
- Frontend lint is not configured for non-interactive CI yet; `next lint` opens the Next.js ESLint setup prompt.
- Dependency installation can still fail in environments where the Python/npm registry proxy returns `403 Forbidden`; CI should use an approved registry mirror or dependency cache.

## Sprint 4.0 — Advertising and Meta Ads limitations

- Automatic Meta Ads OAuth, token refresh, ad account selection and daily insights sync are not active yet.
- Campaign/adset/ad external ID mapping is documented for future additive schema work; current MVP campaign rows remain manual/import oriented.
- Manual advertising import is the supported pilot path and must not be mixed with fake Meta API data.
- Nova Poshta real-key staging validation remains a release blocker for enabling delivery workflow, but it does not block Sprint 4.0 advertising foundation work.

## Sprint 4.0.1 — Remaining advertising validation blockers

- Manual browser-based staging QA for `/advertising`, `/settings/integrations`, Dashboard, Analytics and Import Center still requires staging access and synthetic advertising data.
- `next lint` still uses the deprecated interactive Next.js setup flow; migrate to ESLint CLI configuration in a dedicated tooling task.
- npm still reports environment proxy config warnings; CI should keep using approved dependency caches or registry access to avoid another dependency-restore outage.
