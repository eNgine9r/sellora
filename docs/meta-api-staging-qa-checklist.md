# Meta API Staging QA Checklist — Sprint 6A

Meta Ads API is not active.

Sprint 6A prepares a future staging QA checklist only. No live OAuth, no token storage, no live API calls, and no production sync were implemented.

## Staging checklist

- [ ] Safe staging backend URL.
- [ ] Safe staging frontend URL.
- [ ] Safe staging database.
- [ ] Backup/rollback plan.
- [ ] Test workspace.
- [ ] OWNER test user.
- [ ] MANAGER test user.
- [ ] ANALYST test user.
- [ ] Meta test app.
- [ ] Meta test business/ad account.
- [ ] Redirect URI configured.
- [ ] CORS origin configured.
- [ ] Secrets injected only through environment variables.
- [ ] No secrets in logs.
- [ ] No token shown in UI.
- [ ] Connect attempt OWNER only.
- [ ] MANAGER/ANALYST denied.
- [ ] Disconnect behavior.
- [ ] Expired token behavior.
- [ ] Permission missing behavior.
- [ ] Rate limit/error behavior.

## Pilot-ready rule

Meta Ads API cannot be called pilot-ready until OAuth, token storage, read-only sync, staging QA, workspace isolation QA, browser/mobile QA, and safety scans pass.

Advertising remains feature-frozen and not pilot-ready until the existing Advertising runtime/staging blockers are closed.

## Sprint 6A.1 staging prerequisites

Use `docs/staging-url-inventory.md` as the source for public staging URL placeholders and `docs/meta-oauth-redirect-uri-plan.md` for future OAuth callback planning.

Do not include private staging credentials, DATABASE_URL values, access tokens, app secrets, or token encryption keys in docs, code, screenshots, or PR text.
