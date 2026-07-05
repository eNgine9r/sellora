# Meta Read-only Discovery — Sprint 6C

Sprint 6C adds read-only discovery and sync-preview foundations only.

Meta Ads API is not sync-active.

No scheduled sync jobs, no apply-sync, no ad_metrics writes, no customer/order data transfer, and no Conversions API were implemented.

Manual/CSV remains the active Advertising source.

Advertising remains feature-frozen and not pilot-ready.

Runtime/staging validation is still required before any live sync claim.

## Scope

The discovery foundation exposes safe preview DTOs for future Meta ad accounts and campaigns. It is disabled by default through `META_SYNC_PREVIEW_ENABLED=false` and requires the existing connection foundation to be explicitly enabled before any preview can return data.

## Safe responses

- Account previews return `external_account_id_masked`, name, currency, timezone, source, selection availability, and warnings.
- Campaign previews return `external_campaign_id_masked`, name, status, objective, optional dates, source, and warnings.
- Raw Meta account IDs, campaign IDs, tokens, app secrets, authorization codes, customer data, and order data are never returned.

## Not implemented

- No automatic campaign import into `ad_campaigns`.
- No ad metric writes into `ad_metrics`.
- No scheduled sync or background jobs.
- No apply-sync route or action.
- No Conversions API.

## Sprint 6D — Live read-only Meta foundation and staging validation gate

Sprint 6D adds live read-only client foundation and staging validation gate only.

Meta Ads API is not sync-active.

No scheduled sync jobs, no apply-sync, no ad_metrics writes, no ad_campaigns writes, no customer/order data transfer, and no Conversions API were implemented.

Manual/CSV remains the active Advertising source.

Advertising remains feature-frozen and not pilot-ready.

Real staging OAuth validation, runtime migration QA, Meta App setup, legal review, and browser/mobile QA are still required before pilot-ready claims.
