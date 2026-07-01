# Meta Ads Technical Design — Sprint 4.6 Draft

This is a future implementation contract. It does not add live Meta OAuth, live API calls, token storage logic, sync jobs, or database migrations.

## Proposed backend module boundaries

Future code should keep provider-specific logic isolated under a dedicated integration module, for example:

```text
backend/app/integrations/meta_ads/
  oauth_service.py
  token_service.py
  sync_service.py
  client.py
  schemas.py
  repository.py
```

Responsibilities:

- `client.py`: thin Meta API client wrapper with no business rules; fake client in tests.
- `oauth_service.py`: state generation, callback validation, code exchange orchestration.
- `token_service.py`: token encryption/decryption, refresh scheduling, revoke/disconnect support.
- `sync_service.py`: workspace-scoped campaign and daily metrics sync workflow.
- `repository.py`: database access for Meta connection/account/sync-run records.
- `schemas.py`: request/response contracts that never expose raw tokens.

## Service boundaries

- API routes stay thin and perform auth/RBAC dependency wiring only.
- Services own OAuth validation, workspace checks, sync orchestration, idempotency, and audit events.
- Repositories own database reads/writes and always filter by `workspace_id`.
- Provider clients never know about Sellora RBAC or workspace policies beyond inputs passed by services.

## Future routes

Proposed routes, all workspace-scoped and backend-enforced:

| Route | Method | Role | Purpose |
| --- | --- | --- | --- |
| `/api/v1/integrations/meta/oauth/start` | POST | OWNER | Create state and return official Meta OAuth URL. |
| `/api/v1/integrations/meta/oauth/callback` | GET | server callback | Validate state and exchange token server-side. |
| `/api/v1/integrations/meta/status` | GET | OWNER / allowed read roles | Show masked connection and sync status. |
| `/api/v1/integrations/meta/accounts` | GET | OWNER | List connected ad accounts after OAuth. |
| `/api/v1/integrations/meta/accounts/select` | POST | OWNER | Select workspace ad account. |
| `/api/v1/integrations/meta/sync` | POST | OWNER initially | Trigger read-only sync for a date range. |
| `/api/v1/integrations/meta/disconnect` | POST | OWNER | Revoke/disable connection and audit the event. |

## Future schemas

Response schemas must expose only safe fields:

- connection status;
- provider name;
- masked account/business display name;
- selected account label;
- sync status;
- last successful sync timestamp;
- last safe error category/message.

Response schemas must never expose:

- raw access token;
- refresh token;
- app secret;
- unmasked ad account ID;
- business ID;
- OAuth code;
- workspace ID in user-facing copy.

## Token encryption approach

- Exchange and refresh tokens server-side only.
- Encrypt tokens before persistence using existing secret utilities or an approved KMS/envelope encryption approach.
- Store token expiration and scopes without exposing token values.
- Mask connection/account state in UI.
- Never log token payloads, OAuth callbacks, authorization headers, or raw provider responses.

## Sync job approach

Initial sync should be manual and read-only. Scheduled sync should wait until manual sync is validated in staging.

Required sync behavior:

- sync by selected workspace connection;
- sync by explicit date range;
- paginate through Meta insights safely;
- use backoff for rate limits;
- write sync runs with status: queued/running/succeeded/failed/partial;
- record partial failures per date range where useful;
- retry failed date ranges without duplicating metrics;
- keep manual and CSV import data available if Meta sync fails.

## Idempotency and conflict handling

Future upsert key should consider:

```text
workspace_id + sync_source + external_campaign_id + metric_date
```

Manual/import rows must not be silently overwritten by Meta rows. If a campaign/date has both manual/import and Meta-sourced values, the UI must show source and conflict behavior clearly before any overwrite/merge action.

## Audit logging

Audit events should be created for:

- Meta OAuth start;
- Meta OAuth connected;
- token refresh failed;
- ad account selected;
- manual sync triggered;
- sync succeeded;
- sync failed or partially failed;
- connection disconnected/revoked.

Audit logs must not include raw tokens, raw authorization headers, raw provider payloads, private customer data, or unmasked account identifiers.

## Test plan

Required future tests:

- OAuth state is random, expiring, workspace-scoped, and one-time use.
- Non-OWNER cannot connect/disconnect.
- Workspace A cannot read or sync Workspace B connection.
- Token is encrypted before storage and never appears in response schemas.
- Fake Meta client sync creates/updates campaign and metric rows idempotently.
- Manual/import rows are not silently overwritten by Meta rows.
- Rate-limit and partial failure paths create safe sync statuses.
- Disconnect disables the connection and prevents future sync.

## Staging QA checklist

Before claiming Meta sync readiness in a future sprint:

- Use a controlled staging Meta app and non-production test assets.
- Use secure credentials provided outside the report.
- Do not include real tokens, app secrets, account IDs, business IDs, cookies, workspace IDs, screenshots with secrets, or customer data in QA artifacts.
- Confirm OWNER-only connect/disconnect.
- Confirm token never appears in frontend state, logs, browser console, screenshots, or API responses.
- Confirm workspace isolation with two test workspaces.
- Confirm manual/CSV import fallback still works after connection failure.
- Confirm advertising import remains not pilot-ready unless staging import QA has passed separately.

## Sprint 4.7 implemented fake boundary

Implemented backend skeleton:

```text
backend/app/integrations/meta_ads/
  __init__.py
  schemas.py
  client.py
  fake_client.py
  mapper.py
  sync_service.py
```

Scope:

- `schemas.py` defines typed DTOs and sync candidates for synthetic Meta-like accounts, campaigns, insights rows, issues, and dry-run results.
- `client.py` defines the `MetaAdsClientProtocol` interface: `list_ad_accounts()`, `list_campaigns(account_id)`, and `get_campaign_insights(account_id, date_from, date_to)`.
- `fake_client.py` returns deterministic synthetic accounts, campaigns, zero-denominator rows, and partial/no-data scenarios using fake IDs such as `fake_act_001` and `fake_campaign_001`.
- `mapper.py` maps Meta campaign/insights DTOs into internal sync candidates without writing to the database and without adding orders, revenue, or net profit from Meta.
- `sync_service.py` performs pure dry-run simulation, returns user-safe issues, and never writes to the database.

Still not implemented:

- live OAuth;
- live Meta API calls;
- real token storage;
- production routes;
- scheduled production sync jobs;
- database migrations;
- automatic attribution;
- Conversions API.

Future persistence still requires additive external-source fields and conflict policy before a live sync can write rows. Manual/CSV import remains the active MVP path and must stay available as a fallback.
