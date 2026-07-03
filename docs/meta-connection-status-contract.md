# Meta Connection Status Contract — Sprint 6A

Meta Ads API is not active.

Sprint 6A defines future connection status semantics only. No live OAuth, no token storage, no live API calls, and no production sync were implemented.

## Future backend status values

Backend/API enum values must remain English:

```text
NOT_CONNECTED
MOCK_ONLY
CONNECTING
CONNECTED
NEEDS_REAUTH
PERMISSION_MISSING
TOKEN_EXPIRED
DISCONNECTED
ERROR
```

## Status rules

- [ ] Ukrainian translation happens only at the UI layer.
- [ ] Current production status remains `NOT_CONNECTED` / `MOCK_ONLY`.
- [ ] No `CONNECTED` status without real encrypted token persistence.
- [ ] No active sync status without read-only sync implementation.
- [ ] No pilot-ready wording until OAuth, token storage, read-only sync, staging QA, workspace isolation QA, browser/mobile QA, and safety scans pass.

## Suggested Ukrainian UI labels for later

These labels are future UI copy only and must not replace backend enum values:

| Backend value | Ukrainian UI label |
| --- | --- |
| `NOT_CONNECTED` | Не підключено |
| `MOCK_ONLY` | Лише тестовий режим |
| `CONNECTING` | Підключення триває |
| `CONNECTED` | Підключено |
| `NEEDS_REAUTH` | Потрібне повторне підключення |
| `PERMISSION_MISSING` | Бракує дозволів |
| `TOKEN_EXPIRED` | Термін дії токена минув |
| `DISCONNECTED` | Відключено |
| `ERROR` | Помилка підключення |
