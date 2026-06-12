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
