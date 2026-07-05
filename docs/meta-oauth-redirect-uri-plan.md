# Meta OAuth Redirect URI Plan — Sprint 6A.1

Meta Ads API is not active.

Sprint 6A.1 documents future redirect URI planning only. No live route implementation, no real OAuth redirect, no token storage, and no live API calls were added.

## Future redirect URI options

```text
Staging callback:
https://<backend-staging-domain>/api/v1/integrations/meta-ads/oauth/callback

Production callback:
https://<backend-production-domain>/api/v1/integrations/meta-ads/oauth/callback

Frontend post-connect page:
https://<frontend-staging-domain>/settings/integrations/meta-ads
```

## Rules

- [ ] Callback must be backend-owned for token exchange.
- [ ] Frontend must never receive raw token.
- [ ] Authorization code must not be logged.
- [ ] OAuth state must be validated server-side.
- [ ] Redirect URI must match Meta App settings exactly.
- [ ] Production and staging redirect URIs must be separated.
- [ ] Callback must validate workspace, user, nonce, purpose, expiry, and allowed domain before any future token exchange.

No live OAuth route is implemented in this sprint.
