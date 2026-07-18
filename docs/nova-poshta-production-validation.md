# Nova Poshta Production Validation Guide — Sprint 3.0

This guide prepares Sellora for controlled Nova Poshta validation in staging. It must be used with a controlled test order and a real Nova Poshta account only when the shop owner understands that TTN creation can create operational records in the Nova Poshta account.

## Security rules

- Do not paste Nova Poshta credentials into docs, tickets, screenshots, chat, logs, or fixtures.
- Save credentials only through **Settings → Integrations → Nova Poshta**.
- After save, Sellora must show only a masked saved-key state and must never render the raw credential again.
- Audit events may record that credentials or sender settings changed, but must not include secret values.
- Validate each workspace separately; a workspace must not reuse another workspace’s Nova Poshta connection.

## Required sender settings

TTN creation requires these sender settings before a shipment can be sent to Nova Poshta:

| Setting | Purpose | Validation note |
| --- | --- | --- |
| Sender city ref | Sender city directory reference | Select via city search where possible. |
| Sender warehouse ref | Sender warehouse/address reference | Select only after sender city is selected. |
| Sender counterparty ref | Nova Poshta account sender reference | Enter from the shop’s Nova Poshta account. |
| Sender contact person ref | Sender contact reference | Enter from the shop’s Nova Poshta account. |
| Sender phone | Sender contact phone | Keep it current and do not publish it in docs/screenshots. |

If sender city changes, the selected sender warehouse must be checked again because a warehouse ref is city-specific.

## TTN activation gate

Sellora enables real Nova Poshta writes only when all five conditions are satisfied:

1. The deployment operator has enabled `STAGING_NOVA_POSHTA_ALLOW_WRITES=true` on the backend.
2. The workspace has an active Nova Poshta connection with a saved API key.
3. All sender settings are complete.
4. **Test connection** has successfully verified both the API key and the sender tuple.
5. The workspace `OWNER` has explicitly enabled TTN creation in **Settings → Integrations → Nova Poshta**.

The manager-readable readiness endpoint exposes only these safe booleans and blocker codes. It never returns the API key, masked credential, phone, or sender refs. Credential changes and material sender-setting changes automatically invalidate verification and disable workspace write permission, so the owner must test and enable TTN creation again.

## Manual staging validation steps

1. Open staging as an OWNER for the target workspace.
2. Go to **Settings → Integrations → Nova Poshta**.
3. Confirm the deployment environment allows Nova Poshta writes in the activation checklist. If it does not, ask the deployment operator to enable the documented server flag; do not bypass the gate in application code.
4. Paste the credential into the UI field only.
5. Search for the sender city and select it.
6. Search for the sender warehouse after the city is selected and select it.
7. Fill sender counterparty, contact person, and phone fields from the shop’s Nova Poshta account.
8. Save the credential and complete sender settings together.
9. Confirm the saved credential is masked and the raw value is no longer visible.
10. Click **Test connection**. Confirm the API key and complete sender tuple pass, or fix the localized field-specific error.
11. Confirm the activation checklist shows the first four conditions as ready.
12. Click **Enable TTN creation** as the workspace owner and confirm the fifth condition becomes ready.
13. Create a controlled test order with non-sensitive customer data.
14. Open the order details and choose **Create shipment from order**.
15. Fill recipient details, select Nova Poshta city and warehouse, and save the shipment as a draft.
16. Open the shipment details and create the TTN only when the shop is ready for a real Nova Poshta-side record.
17. Confirm the TTN/tracking number is saved on the shipment.
18. Confirm the linked order shows shipment/tracking information.
19. Try the status sync action if available and confirm failures use a safe localized message.
20. Confirm creating a second TTN for the same shipment is blocked or clearly warned.
21. Confirm logs and audit records do not contain the raw credential.

## Expected behavior

- Credential management, connection verification, and write-permission changes are OWNER-only.
- Safe readiness state is available to MANAGER users so order creation can explain the exact non-secret blocker.
- Shipment creation, TTN creation, status changes, and status sync require at least MANAGER permissions.
- ANALYST users can read shipment information but cannot mutate shipments or Nova Poshta settings.
- TTN creation sets shipment delivery data but does **not** automatically complete the order.
- Order and shipment statuses remain separate business concepts.
- City and warehouse search show loading, empty, and safe error states.
- Raw Nova Poshta API payloads and stack traces must not appear in the UI.

## Known limitations

- Automated Nova Poshta status updates are not fully connected; use manual sync where available.
- TTN cancellation through Nova Poshta is not fully production-validated yet.
- Real credential validation requires staging access to a controlled shop account.
- Refs for counterparty and contact person may need to be copied from the shop’s Nova Poshta account until a dedicated account-directory UI is added.

## Sprint 3.1 delivery workflow QA

1. Open `/shipments` and confirm search, filters and pagination work without horizontal overflow.
2. Open a shipment detail panel and verify Order, Customer, Recipient, Nova Poshta, TTN and Status sections.
3. Create a TTN only for a controlled synthetic/staging order and confirm duplicate creation is blocked.
4. Copy the TTN from shipment list, shipment detail and order detail when available.
5. Run status sync only after TTN exists and confirm errors are safe if Nova Poshta is unavailable.
6. Confirm printable/downloadable TTN documents are presented as a known limitation, not as a fake document.
7. Confirm logs and audit metadata do not contain raw API keys or raw third-party payloads.

## Sprint 3.2 staging prerequisite

Before production-like validation, complete `docs/nova-poshta-staging-validation.md` with a controlled staging account. Confirm credential masking, sender settings reload, order → shipment consistency, TTN duplicate prevention, status sync safe-unavailable behavior, mobile usability, and audit/logging safety. Do not proceed with a real TTN unless the shop owner approves a controlled test shipment.

## Sprint 3.2.1 environment prerequisite

Backend tests, frontend typecheck/build, and regression scripts now pass in the recovered local environment. Production-like Nova Poshta validation must still wait for a controlled staging credential and must not include real keys, real TTNs, sender refs, customer data or screenshots in source control or PR text.
