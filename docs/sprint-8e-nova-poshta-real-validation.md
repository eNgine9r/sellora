# Sprint 8E — Nova Poshta Real Validation

## Existing integration inventory

Audited `NovaPoshtaClient`, `NovaPoshtaSettingsService`, `NovaPoshtaDirectoryService`, `NovaPoshtaShipmentService`, Nova Poshta API routes, shipment TTN fields, encrypted integration credentials, fake tests, Settings → Integrations UI, shipment TTN controls and previous Nova Poshta regression scripts.

## Actual provider operations

See `docs/nova-poshta-provider-contract.md`. The implemented operations are key validation, city search, warehouse search, TTN creation and manual tracking refresh. Provider cancellation/delete is not implemented in the current repository.

## Configuration and secrets

API keys remain in encrypted integration credentials and settings responses expose only `masked_api_key`. TTN provider writes now require the backend server-side `STAGING_NOVA_POSHTA_ALLOW_WRITES=true` flag, while CI tests use an explicit service override with deterministic fake clients.

## Sender contract

The current sender contract requires `sender_city_ref`, `sender_warehouse_ref`, `sender_counterparty_ref`, `sender_contact_ref` and `sender_phone`. Missing sender data blocks TTN creation before provider write.

## City/warehouse discovery

City and warehouse discovery remain read-only provider calls using the existing configured workspace credential. Real-provider discovery must be validated from staging with secrets; local tests use deterministic fakes.

## TTN eligibility

TTN creation requires an active Nova Poshta shipment with workspace-local shipment/order, recipient name, phone, destination city/warehouse, declared value, sender settings and no existing TTN/document ref.

## TTN creation

Backend TTN creation now checks the server-side write flag before calling `InternetDocument.save`. If writes are disabled, the provider is not called and Sellora shipment/order/inventory state remains unchanged.

## Idempotency

Existing active TTN/document fields block duplicate creation. A process-local in-progress guard blocks concurrent duplicate attempts for the same workspace/shipment before provider write. Staging must still prove duplicate-click behavior against the real provider.

## Retry policy

Read-only operations may be retried manually by the user. Non-idempotent provider writes are not automatically retried. Provider write failures return safe errors without raw provider payloads.

## Failure compensation

Provider failure before document creation leaves the shipment local/draft-like and TTN fields empty. Provider success followed by local persistence failure still requires real staging validation and a future manual-reconciliation policy because no new persistence table or background compensation workflow was added.

## Tracking synchronization

Manual status sync stores raw provider status and updates the normalized Sellora shipment status only for deterministic mappings. Sync does not mutate orders, payments, inventory or finance state.

## Status mapping

See `docs/nova-poshta-status-mapping.md`. Unknown status keeps the previous normalized shipment status and requires support review.

## TTN cancellation

Provider cancellation/delete is not implemented in the current repository. Sprint 8E does not add a fake cancellation API or UI; controlled provider cleanup remains a staging/manual procedure.

## RBAC

OWNER remains responsible for integration configuration. MANAGER-or-higher can use operational provider read/TTN routes according to existing route policy. ANALYST provider mutations remain denied by backend role dependencies.

## Workspace isolation

Integration settings, credentials, directory calls and shipment TTN/status actions are scoped by `workspace_id`. Cross-workspace TTN creation is rejected by the workspace-scoped connection and shipment lookups.

## Audit and PII safety

Audit events record provider action categories and safe error codes only. API key, full provider payload, full address and complete recipient phone must not be committed or exposed in logs/artifacts.

## Browser/mobile result

Not executed in this environment because real staging credentials, Nova Poshta key and guarded browser workflow were not available.

## Console/network result

Not executed against real provider. Local validation confirms no provider write happens when the server-side write flag is disabled.

## Performance

Real durations for key validation, city search, warehouse lookup, TTN creation, tracking refresh and cancellation remain staging-only evidence.

## Cleanup

No real provider document was created locally. QA8E cleanup remains required for the guarded staging workflow.

## Issues found and fixes

- Added backend write-flag enforcement for TTN creation.
- Added process-local in-progress duplicate protection for TTN creation.
- Added deterministic provider status normalization with unknown-status preservation.
- Documented provider cancellation as unsupported rather than fabricating a flow.

## Remaining limitations

Real Nova Poshta key validation, real city/warehouse discovery, controlled TTN creation, tracking sync, browser/mobile evidence and provider cleanup remain blocked until approved staging secrets and write flag are available.

## Sprint status

Sprint 8E — BLOCKED ⚠️ for final approval because no real Nova Poshta credentials or controlled staging write workflow were available in this environment.

## Pilot recommendation

Controlled guided pilot remains GREEN for local shipments and existing orders/inventory flows. Nova Poshta provider actions must remain disabled until the guarded staging workflow proves the real-provider gates.
