# Meta Token Storage Design — Sprint 6A

Meta Ads API is not active.

This is a design document only. Sprint 6A prepares secure token storage requirements for a future sprint. No live OAuth, no token storage, no live API calls, and no production sync were implemented.

## Future storage requirements

- [ ] Encrypted access token storage.
- [ ] Token never returned to frontend.
- [ ] Masked token display only.
- [ ] Token fingerprint for support/debugging.
- [ ] Token expiry tracking.
- [ ] `last_refresh_at` tracking.
- [ ] `revoked_at` tracking.
- [ ] `disconnected_at` tracking.
- [ ] Rotation/reconnect path.
- [ ] Audit log on connect/disconnect/refresh/failure.
- [ ] No raw token in logs.

## Suggested future table design

Do not add this migration in Sprint 6A. This is design for future Sprint 6B.

```text
meta_ad_connections:
  id
  workspace_id
  provider
  connection_status
  external_business_id nullable
  external_ad_account_id nullable
  account_name nullable
  currency nullable
  timezone nullable
  encrypted_access_token
  token_fingerprint
  token_expires_at
  scopes
  connected_by_user_id
  connected_at
  last_synced_at nullable
  disconnected_at nullable
  revoked_at nullable
  created_at
  updated_at
  deleted_at nullable
```

## Encryption and redaction expectations

Future implementation must encrypt provider tokens before database persistence, return only masked connection metadata to the frontend, and include automated tests proving raw tokens do not appear in API responses, logs, audit payloads, fixtures, or documentation.

## Sprint 6A.1 environment prerequisite note

Future token storage prerequisites are documented in `docs/meta-env-vars-plan.md`. Sprint 6A.1 does not add token persistence, encryption-key handling, or a `meta_ad_connections` migration.

## Sprint 6B — Meta encrypted connection foundation

Sprint 6B adds encrypted token storage infrastructure and connection records behind feature gates.

Meta Ads API is not sync-active.

Live sync, scheduled jobs, apply-sync, and Conversions API are not implemented.

Real OAuth validation requires staging URLs, legal review, Meta App setup, and safe PostgreSQL runtime migration QA.

Advertising remains feature-frozen and not pilot-ready.
