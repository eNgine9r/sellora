# Meta Staging Validation Gate — Sprint 6D

Sprint 6D adds live read-only client foundation and staging validation gate only.

Meta Ads API is not sync-active.

No scheduled sync jobs, no apply-sync, no ad_metrics writes, no ad_campaigns writes, no customer/order data transfer, and no Conversions API were implemented.

Manual/CSV remains the active Advertising source.

Advertising remains feature-frozen and not pilot-ready.

Real staging OAuth validation, runtime migration QA, Meta App setup, legal review, and browser/mobile QA are still required before pilot-ready claims.

## Gate

`META_STAGING_VALIDATION_ENABLED=false` by default.

When disabled, staging validation returns a safe not-ready response and performs no live calls. When enabled in a controlled non-production environment, validation still requires a workspace-scoped connection record, connected status, encrypted token, token-storage configuration, and production sync disabled.

## Validation report

The report is preview-only and includes `sync_active=false` and `writes_performed=false`. It reports counts for account, campaign, and insights preview samples without writing Meta data to Sellora advertising tables.
