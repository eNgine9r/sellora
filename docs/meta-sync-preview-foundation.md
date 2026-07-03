# Meta Sync Preview Foundation — Sprint 6C

Sprint 6C adds read-only discovery and sync-preview foundations only.

Meta Ads API is not sync-active.

No scheduled sync jobs, no apply-sync, no ad_metrics writes, no customer/order data transfer, and no Conversions API were implemented.

Manual/CSV remains the active Advertising source.

Advertising remains feature-frozen and not pilot-ready.

Runtime/staging validation is still required before any live sync claim.

## Preview route behavior

`GET /api/v1/integrations/meta-ads/sync/preview` returns preview-only delivery metrics from the read-only client boundary when all readiness checks pass. It uses “preview only” language and exposes no raw external identifiers or token fields.

## Readiness checks

- `META_SYNC_PREVIEW_ENABLED` must be explicitly enabled.
- `META_CONNECTIONS_ENABLED` must be enabled.
- A workspace-scoped Meta connection must exist.
- Connection status must be `CONNECTED` or a safe explicit test preview state.
- A connected live foundation must have encrypted token material available before live preview can proceed.
- `META_SYNC_ENABLED` must remain disabled for Sprint 6C preview mode.

## Write safety

The preview service does not call repositories that mutate Advertising data. It does not write to `ad_campaigns`, does not write to `ad_metrics`, does not create sync runs, and does not schedule background work.

## Sprint 6D — Live read-only Meta foundation and staging validation gate

Sprint 6D adds live read-only client foundation and staging validation gate only.

Meta Ads API is not sync-active.

No scheduled sync jobs, no apply-sync, no ad_metrics writes, no ad_campaigns writes, no customer/order data transfer, and no Conversions API were implemented.

Manual/CSV remains the active Advertising source.

Advertising remains feature-frozen and not pilot-ready.

Real staging OAuth validation, runtime migration QA, Meta App setup, legal review, and browser/mobile QA are still required before pilot-ready claims.
