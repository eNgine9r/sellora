# Meta Environment Variables Plan — Sprint 6A.1

Meta Ads API is not active.

Sprint 6A.1 documents future environment variables only. No live OAuth, no token storage, no live API calls, and no production sync were implemented.

## Future environment variables

| Variable | Scope | Required now? | Notes |
| --- | --- | --- | --- |
| `META_APP_ID` | Server-side config; public identifier can be referenced safely only when needed | No | Set in hosting provider in future Sprint 6B+ |
| `META_APP_SECRET` | Server-only secret | No | Never expose to frontend, logs, docs, screenshots, or PR text |
| `META_OAUTH_REDIRECT_URI` | Server-side config | No | Must match Meta App settings exactly in future implementation |
| `META_API_VERSION` | Server-side config | No | Use an explicit supported version after official-doc verification |
| `META_TOKEN_ENCRYPTION_KEY` | Server-only secret | No | Required only before encrypted token persistence is implemented |
| `META_WEBHOOK_VERIFY_TOKEN` | Future-only server secret | No | Future webhook/CAPI work only, not part of read-only OAuth MVP |

## Safe placeholder example

```text
META_APP_ID=<set-in-hosting-provider>
META_APP_SECRET=<server-only-secret>
META_OAUTH_REDIRECT_URI=https://<backend-domain>/api/v1/integrations/meta-ads/oauth/callback
META_TOKEN_ENCRYPTION_KEY=<server-only-secret>
```

## Safety rules

- [ ] Do not add real values.
- [ ] Do not commit `.env` files.
- [ ] Mark secrets as server-only.
- [ ] `NEXT_PUBLIC` must not be used for secrets.
- [ ] Frontend may only receive safe public status.
- [ ] App secret and token encryption key must never be exposed to frontend.
- [ ] Do not require these variables at app startup until live OAuth implementation is approved.
