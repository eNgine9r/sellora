# Meta Live OAuth Backend Foundation — Sprint 6B

Sprint 6B adds encrypted token storage infrastructure and connection records behind feature gates.

Meta Ads API is not sync-active.

Live sync, scheduled jobs, apply-sync, and Conversions API are not implemented.

Real OAuth validation requires staging URLs, legal review, Meta App setup, and safe PostgreSQL runtime migration QA.

Advertising remains feature-frozen and not pilot-ready.

## Feature gates

All live foundations are disabled by default:

- `META_CONNECTIONS_ENABLED=false`
- `META_LIVE_OAUTH_ENABLED=false`
- `META_TOKEN_STORAGE_ENABLED=false`
- `META_SYNC_ENABLED=false`

The app must start without Meta environment variables. Missing configuration returns safe disabled/configuration responses instead of redirects.

## Backend route foundation

Future live routes are added under `/api/v1/integrations/meta-ads`:

- `GET /status` — read-only safe connection status.
- `POST /oauth/start` — OWNER-only guarded state creation and authorization URL construction only when explicitly enabled/configured.
- `POST /oauth/callback` — OWNER-only guarded state validation and token exchange interface; tests use synthetic tokens only.
- `POST /disconnect` — OWNER-only disconnect that clears stored token material.

## Not implemented in Sprint 6B

- No read-only Meta insights sync.
- No scheduled jobs.
- No apply-sync.
- No Conversions API.
- No customer/order data transfer to Meta.
- No production-ready OAuth claim.

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
