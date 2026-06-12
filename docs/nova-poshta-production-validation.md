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

## Manual staging validation steps

1. Open staging as an OWNER for the target workspace.
2. Go to **Settings → Integrations → Nova Poshta**.
3. Paste the credential into the UI field only, then save.
4. Confirm the saved state is masked and the raw value is no longer visible.
5. Click **Test connection** and confirm either a connected state or a safe localized error.
6. Search for the sender city and select it.
7. Search for the sender warehouse after the city is selected and select it.
8. Fill sender counterparty, contact person, and phone fields from the shop’s Nova Poshta account.
9. Save sender settings without re-entering the credential and confirm the masked key remains saved.
10. Create a controlled test order with non-sensitive customer data.
11. Open the order details and choose **Create shipment from order**.
12. Fill recipient details, select Nova Poshta city and warehouse, and save the shipment as a draft.
13. Open the shipment details and create the TTN only when the shop is ready for a real Nova Poshta-side record.
14. Confirm the TTN/tracking number is saved on the shipment.
15. Confirm the linked order shows shipment/tracking information.
16. Try the status sync action if available and confirm failures use a safe localized message.
17. Confirm creating a second TTN for the same shipment is blocked or clearly warned.
18. Confirm logs and audit records do not contain the raw credential.

## Expected behavior

- Credential management is OWNER-only.
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
