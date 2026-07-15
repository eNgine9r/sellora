# Nova Poshta provider contract — Sprint 8E

## Actual provider operations in the repository

| Sellora action | Provider operation from current code | Read/write | Current local state |
| --- | --- | --- | --- |
| Validate key | `Address.getAreas` via `NovaPoshtaClient.test_connection()` | Read | CI fake-client PASS; real-provider staging pending |
| Search city | `Address.searchSettlements` with `CityName` and `Limit` | Read | CI fake-client PASS; real-provider staging pending |
| Search warehouse | `Address.getWarehouses` with `CityRef`, optional `FindByString`, `Limit` | Read | CI fake-client PASS; real-provider staging pending |
| Create TTN | `InternetDocument.save` through `create_internet_document()` | Write | Backend write flag and duplicate guard implemented; real-provider staging pending |
| Track TTN | `TrackingDocument.getStatusDocuments` | Read | Manual sync implemented with status normalization; real-provider staging pending |
| Cancel/delete TTN | Not implemented in current repository | Write | Deferred; no fake cancellation UI/API is added |

## Sanitized request/response notes

Provider requests are created server-side with the encrypted workspace credential decrypted only in backend service code. The API key is never returned in settings responses; frontend receives only `masked_api_key`.

TTN creation stores only the TTN number, provider document ref, provider status and sync timestamps already supported by the shipment model. Full provider payload storage is not introduced in Sprint 8E.
