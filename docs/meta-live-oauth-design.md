# Meta Live OAuth Design — Sprint 6A

Meta Ads API is not active.

This is a design document only. Sprint 6A prepares setup, security, OAuth, token storage, and QA design only. No live OAuth, no token storage, no live API calls, and no production sync were implemented.

## Future live OAuth flow

1. OWNER opens Integrations → Meta Ads.
2. Backend creates signed OAuth state.
3. State includes `workspace_id`, `user_id`, `nonce`, `issued_at`, `expires_at`, and `purpose`.
4. User is redirected to Meta OAuth in a future sprint only.
5. Meta redirects back to the Sellora callback URL in a future sprint only.
6. Backend validates state, expiry, nonce, workspace, user, and purpose.
7. Backend exchanges authorization code for token in a future sprint only.
8. Backend stores encrypted token only in future Sprint 6B or later.
9. Backend creates connection record only in future Sprint 6B or later.
10. UI shows connected status only after real safe persistence is implemented and staging QA passes.

## OAuth state contract

The future signed state should be short-lived, one-time-use, and workspace-scoped. It must bind the connect attempt to the current OWNER and workspace so a callback cannot connect a Meta account to the wrong tenant.

Suggested future fields:

```text
workspace_id
user_id
nonce
issued_at
expires_at
purpose = META_ADS_CONNECT
return_path
```

## Security requirements

- [ ] OWNER-only connect.
- [ ] Workspace-scoped OAuth state.
- [ ] State expiry.
- [ ] Nonce validation.
- [ ] Callback domain allowlist.
- [ ] CSRF protection.
- [ ] No token in frontend URL after callback.
- [ ] No token in logs.
- [ ] No token in response body.
- [ ] No token in localStorage.
- [ ] No token in docs/tests.

## Sprint 6A implementation boundary

Sprint 6A does not add a live OAuth route, does not redirect to a real Meta OAuth URL, does not exchange authorization codes, and does not persist connection records. The existing mock OAuth boundary remains a mock/future-ready safety tool only.

## Official references to re-check

- Meta Login manual flow guide: https://developers.facebook.com/documentation/facebook-login/guides/advanced/manual-flow
- Meta Login security guide: https://developers.facebook.com/documentation/facebook-login/security

## Sprint 6A.1 prerequisite note

The future callback URI is documented in `docs/meta-oauth-redirect-uri-plan.md`. Sprint 6A.1 does not implement the route, redirect to Meta, exchange authorization codes, or store tokens.
