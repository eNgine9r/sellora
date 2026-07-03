# Meta Audit Logging Design — Sprint 6A

Meta Ads API is not active.

Sprint 6A documents future audit logging only. No live OAuth, no token storage, no live API calls, no persistent Meta audit table, and no production sync were implemented.

## Future audit events

```text
meta_ads_connect_started
meta_ads_connect_succeeded
meta_ads_connect_failed
meta_ads_disconnected
meta_ads_token_refreshed
meta_ads_token_refresh_failed
meta_ads_permission_missing
meta_ads_sync_started
meta_ads_sync_succeeded
meta_ads_sync_failed
```

## Payload safety rules

- [ ] No raw token.
- [ ] No client secret.
- [ ] No authorization code.
- [ ] No customer PII.
- [ ] No order/customer payload.
- [ ] No cookies.
- [ ] No DATABASE_URL.
- [ ] No real ad account ID in public logs.
- [ ] IDs masked or internal-only where needed.

## Future audit payload shape

Future payloads should include internal IDs, workspace ID, actor ID, event name, status, timestamp, safe provider metadata, and a redacted error class when needed. Provider secrets, customer/order payloads, raw external IDs, and authorization artifacts must be excluded.
