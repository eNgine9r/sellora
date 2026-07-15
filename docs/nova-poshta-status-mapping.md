# Nova Poshta status mapping — Sprint 8E

Sprint 8E does not add new backend shipment enums. Provider statuses are stored as raw provider context and normalized only when a deterministic mapping exists.

| Provider status marker | Sellora shipment status |
| --- | --- |
| `delivered`, `отримано`, `доставлено` | `DELIVERED` |
| `return`, `повер`, `відмова` | `RETURNED` |
| `in transit`, `дороз`, `пряму`, `відправ` | `IN_TRANSIT` |
| `arrived`, `прибул`, `відділен` | `ARRIVED` |
| Unknown/unmapped | Keep previous normalized Sellora status |

Unknown provider status must not fabricate delivery completion. The UI should communicate: `Статус перевізника потребує перевірки` while preserving the sanitized raw provider status for support diagnostics.

Manual tracking refresh must not deduct stock, release reservations, restore stock or mutate order/payment state.
