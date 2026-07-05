# Meta Connection Records — Sprint 6B

Sprint 6B adds encrypted token storage infrastructure and connection records behind feature gates.

Meta Ads API is not sync-active.

Live sync, scheduled jobs, apply-sync, and Conversions API are not implemented.

Real OAuth validation requires staging URLs, legal review, Meta App setup, and safe PostgreSQL runtime migration QA.

Advertising remains feature-frozen and not pilot-ready.

## Scope

`meta_ad_connections` is a workspace-scoped foundation table for future Meta Ads OAuth connections. It is not a sync table and it must not be used to import live advertising data during Sprint 6B.

## Stored fields

The table stores connection metadata, status, nullable external identifiers, and an encrypted access token only when all backend feature gates and encryption configuration are explicitly enabled. There is no raw `access_token` column and no refresh token column.

## Safety rules

- `workspace_id` is required for every connection record.
- Backend/API enum values remain English: `NOT_CONNECTED`, `CONNECTING`, `CONNECTED`, `DISCONNECTED`, and error statuses.
- Tokens are server-only and are never returned to frontend responses.
- Support/debugging uses a one-way token fingerprint only.
- Disconnect clears stored encrypted token material and marks the connection `DISCONNECTED`.
- Sync remains future work and must pass separate staging QA before activation.

## Sprint 6C — Meta read-only discovery and sync-preview foundation

Sprint 6C adds read-only discovery and sync-preview foundations only.

Meta Ads API is not sync-active.

No scheduled sync jobs, no apply-sync, no ad_metrics writes, no customer/order data transfer, and no Conversions API were implemented.

Manual/CSV remains the active Advertising source.

Advertising remains feature-frozen and not pilot-ready.

Runtime/staging validation is still required before any live sync claim.
