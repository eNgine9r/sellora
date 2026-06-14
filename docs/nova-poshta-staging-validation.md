# Nova Poshta Staging Validation — Sprint 3.2

This checklist is for controlled staging validation only. Do not paste real Nova Poshta API keys, real TTN values, sender refs, customer phones, workspace IDs, screenshots with credentials, or private order data into code, docs, tickets, tests, logs, or chat.

Use a controlled staging account, a controlled test order, synthetic customer data, masked credential display, and safe logs. Real TTN creation can create real records in a Nova Poshta account, so run the TTN step only when the shop owner has approved a controlled test shipment.

## Required staging flow

1. Open the staging frontend.
2. Log in as `OWNER`.
3. Open `/settings/integrations`.
4. Save the Nova Poshta API key.
5. Confirm only the masked key is shown after save.
6. Run **Test connection**.
7. Search sender city.
8. Select sender city.
9. Confirm warehouse search is enabled after city selection.
10. Search sender warehouse.
11. Select sender warehouse.
12. Save sender settings without re-entering the API key.
13. Reload the page and confirm settings persist.
14. Create or select a controlled customer with synthetic data.
15. Create a controlled order with that customer.
16. Create shipment from the order.
17. Confirm order/customer/recipient data prefill.
18. Select recipient city and warehouse.
19. Create shipment draft.
20. Create TTN only if safe to do so.
21. Confirm tracking number is saved.
22. Confirm tracking appears on shipment detail.
23. Confirm tracking appears on order detail.
24. Try duplicate TTN creation.
25. Confirm duplicate is blocked.
26. Run status sync.
27. Confirm safe status update or safe unavailable message.
28. Confirm audit/logs contain no raw API key.
29. Confirm no raw third-party payload is shown in UI.
30. Confirm mobile layout is usable at 375px, 390px, 430px, 768px and desktop.

## Credential edge cases

- No API key saved: show a localized message that the Nova Poshta key is not saved.
- Invalid, expired or revoked API key: show a localized connection failure and do not expose raw API payloads.
- API key saved but sender settings missing: block TTN creation with a human-readable sender settings message.
- Sender settings saved without re-entering key: keep the existing encrypted credential and show only masked state.
- Key rotation: save a new key, keep raw value hidden after save, and write safe audit metadata only.

Expected UI messages include:

- `Ключ Нової Пошти не збережено.`
- `Не вдалося перевірити API-ключ Нової Пошти.`
- `Заповніть налаштування відправника перед створенням ТТН.`
- `Ключ збережено та приховано з міркувань безпеки.`

## Sender settings edge cases

- City not selected: warehouse search remains disabled.
- Warehouse search before city selected: UI prompts the user to select city first.
- City changed after warehouse selected: stale warehouse ref and visible warehouse query are cleared.
- Sender counterparty/contact/phone missing: TTN creation returns a safe sender-settings error before any shipment is confirmed.
- Sender settings save/reload: reload `/settings/integrations` and confirm sender refs persist while raw credential remains hidden.

## Recipient and customer edge cases

- Order has no customer or historical imported order lacks customer: shipment/TTN creation is blocked with a safe missing-customer message.
- Customer or recipient phone missing: show `Вкажіть номер телефону отримувача.` / `Enter the recipient phone number.`
- Recipient city missing: show `Оберіть місто отримувача.` / `Select the recipient city.`
- Recipient warehouse missing: show `Оберіть відділення отримувача.` / `Select the recipient warehouse.`
- Shipment order/customer mismatch: backend validation must keep shipment customer aligned with the order customer and workspace.

## TTN edge cases

- Shipment has no TTN: create action is available only when required data exists.
- Shipment already has TTN: create action is disabled and duplicate attempts return a localized warning.
- Nova Poshta validation error or API unavailable: show safe localized error text and no raw third-party payload.
- TTN creation response missing expected fields: do not save tracking; ask the user to check the Nova Poshta account before retrying.
- Multiple quick clicks: create button stays disabled while loading and cache invalidates after success.

## Delivery status sync edge cases

- Sync without TTN: action remains disabled in UI and backend blocks the request.
- Sync with TTN: loading state is visible; success updates last sync/external status helper text.
- Nova Poshta status unavailable, unknown or empty: show a safe unavailable message and keep internal status badge localized.
- API failure: no raw payload is shown and audit metadata stores only a safe error code.

## RBAC and workspace validation

- `OWNER`: can save/test Nova Poshta settings, manage sender settings, create shipments, create TTN and sync status.
- `MANAGER`: can create shipments, create TTN and sync status; cannot manage API key under current rules.
- `ANALYST`: can view shipment data; cannot mutate shipments, create TTN, sync status or manage API key.
- Workspace A cannot see or use Workspace B credentials, shipments, orders, TTN creation or status sync.

## Audit and logging safety

Audit/log checks must confirm that raw Nova Poshta credentials, raw third-party payloads, private customer data and real TTN values are not persisted in audit metadata. Safe metadata may include provider name, action name, non-secret status, and safe error codes such as `TTN_CREATE_FAILED`, `TTN_CREATE_INCOMPLETE` or `STATUS_SYNC_FAILED`.

## Mobile QA

Verify `/settings/integrations`, `/orders`, order detail, `/shipments`, shipment create modal, shipment detail panel, Nova Poshta panel, TTN actions and status sync action at 375px, 390px, 430px, 768px and desktop. There should be no body-level horizontal overflow, action buttons must remain reachable, modal content must scroll internally when needed, and dark/light contrast must remain readable.

## Sprint 3.2.1 environment validation result

Automated backend and frontend validation was recovered in the current workspace after dependencies became available locally. The previous blocker was environmental: Python and Node dependencies were missing locally, and package installation had been blocked by registry/proxy `403 Forbidden` responses rather than by Sellora source code.

Current validation status:

- Backend `compileall`, full `pytest`, and FastAPI app import pass locally.
- Frontend TypeScript typecheck and production build pass locally using the restored `frontend/node_modules` state.
- `npm run lint` still reaches the existing interactive Next.js ESLint setup prompt; treat this as a known tooling setup task rather than a Sprint 3.2 delivery blocker.
- Regression scripts pass, including Nova Poshta production, order/customer linking, shipment TTN/status, and staging edge-case checks.
- Real Nova Poshta staging validation remains blocked until a controlled shop-owned API key is provided. No real TTN creation was executed and no real key, sender ref, tracking number, customer data, or screenshot was committed.

Recommended CI follow-up:

1. Ensure backend CI installs `backend/requirements.txt` from an allowed Python package index or cache.
2. Ensure frontend CI restores dependencies from an approved npm registry/cache before running typecheck/build.
3. Add a frontend lockfile in a dedicated dependency-hygiene change if the team wants stricter reproducible npm installs.
4. Execute this checklist with a controlled real key only in staging and keep raw credentials outside code, docs, logs and PR text.
