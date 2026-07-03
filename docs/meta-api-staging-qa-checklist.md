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

## Sprint 6B — Meta encrypted connection foundation

Sprint 6B adds encrypted token storage infrastructure and connection records behind feature gates.

Meta Ads API is not sync-active.

Live sync, scheduled jobs, apply-sync, and Conversions API are not implemented.

Real OAuth validation requires staging URLs, legal review, Meta App setup, and safe PostgreSQL runtime migration QA.

Advertising remains feature-frozen and not pilot-ready.

## Sprint 6C — Meta read-only discovery and sync-preview foundation

Sprint 6C adds read-only discovery and sync-preview foundations only.

Meta Ads API is not sync-active.

No scheduled sync jobs, no apply-sync, no ad_metrics writes, no customer/order data transfer, and no Conversions API were implemented.

Manual/CSV remains the active Advertising source.

Advertising remains feature-frozen and not pilot-ready.

Runtime/staging validation is still required before any live sync claim.

## Sprint 6D — Live read-only Meta foundation and staging validation gate

Sprint 6D adds live read-only client foundation and staging validation gate only.

Meta Ads API is not sync-active.

No scheduled sync jobs, no apply-sync, no ad_metrics writes, no ad_campaigns writes, no customer/order data transfer, and no Conversions API were implemented.

Manual/CSV remains the active Advertising source.

Advertising remains feature-frozen and not pilot-ready.

Real staging OAuth validation, runtime migration QA, Meta App setup, legal review, and browser/mobile QA are still required before pilot-ready claims.
