# Task 2 — Meta Ads backend implementation report

## Summary

Implemented real, feature-gated server-side Ads OAuth, durable single-use workspace/OWNER state, encrypted credentials, explicit granted-account selection and bounded read-only manual daily sync. No production database, environment, provider credential, feature activation, external campaign/budget mutation, push or deployment was performed. Working Instagram configuration and credential paths were left unchanged.

Migration 202610200039 extends038. It adds hash-only OAuth state, connection generation/last-attempt metadata, and partial unique live campaign/metric identity indexes. Existing legacy/manual/CSV rows are not rewritten. OAuth state has RLS enabled with no public/anon policies; application repository scoping follows the established backend DB-role convention.

## Frontend API contract

All paths below are under /api/v1/integrations/meta-ads. All JSON operations use the existing authenticated session/workspace mechanism. No new token is returned to the frontend.

### GET /status

Existing minimum ANALYST read. Returns:
- provider: "meta_ads"
- workspace_id: UUID string
- connection_status: existing enum NOT_CONNECTED | MOCK_ONLY | CONNECTING | CONNECTED | NEEDS_REAUTH | PERMISSION_MISSING | TOKEN_EXPIRED | DISCONNECTED | ERROR
- connected, implemented, live_oauth_enabled, connections_enabled, token_storage_enabled, sync_enabled, configured, can_connect, can_sync, account_selection_required: boolean
- blockers: string array
- reason: string or null; message: string
- account_name, currency, timezone: string or null
- token_expires_at, connected_at, disconnected_at, last_synced_at, last_sync_attempt_at: ISO datetime or null
- last_error_code, last_error_message: safe string or null
- legacy compatibility fields external_ad_account_id_masked, token_fingerprint, audit_event: null on this live implementation; frontend must not depend on fingerprint or audit stubs.

Configuration blockers: feature_disabled, live_oauth_disabled, token_storage_disabled, unsupported_api_version, missing_required_configuration, invalid_encryption_configuration. can_sync additionally requires the sync flag, a connected account and explicit selection.

### POST /oauth/start

OWNER only. No body. Returns the status fields plus authorization_url (HTTPS Facebook URL) and state_expires_at (ISO datetime). Frontend navigates to authorization_url. State is unpredictable and only its SHA-256 digest is stored. Starting a new attempt invalidates an older attempt/credential generation and clears account selection.

### GET /oauth/callback

Explicit public forwarding-only endpoint, feature/config gated. Accepts provider code and state or an error. Returns303 to the fixed configured Ads frontend callback with code/state, or error=access_denied. It does not consume state, exchange code, or mutate connection data. no-store/no-referrer headers apply including validation failures. A dedicated ASGI middleware removes the callback query from Uvicorn's access-log scope while preserving a private inner scope for validation.

Frontend route: /settings/integrations/meta-ads/callback. Remove query credentials from browser history immediately; send authenticated OWNER POST below with the original state/code and initiating workspace. On cancellation show a localized error without attempting exchange. Never log code, state, token or callback URLs.

### POST /oauth/callback

OWNER only. Request {"state": string, "code": string}; max lengths2048/4096. Returns status fields plus token_stored: true. Success is CONNECTED with account_selection_required: true. It verifies granted ads_read; connection success alone never selects an account. State is atomically deleted and committed before network I/O. Replays, expiry, mismatched user/workspace and tampering fail400 invalid_state.

### GET /accounts

OWNER only. Returns:
{
  "accounts": [
    {
      "external_account_id": "act_<numeric>",
      "name": string,
      "currency": string,
      "timezone": string,
      "selectable": boolean,
      "reason": null | "currency_mismatch"
    }
  ],
  "selected_account_id": string | null,
  "workspace_currency": string,
  "workspace_timezone": string
}
IDs are non-secret identifiers exposed only in this authenticated, scoped selection API. Empty accounts is a real empty state. No first-account default.

### POST /account

OWNER only. Request {"external_account_id": "act_<numeric>"} (1–40 digits). Returns status fields. Re-fetches provider-granted accounts, rejects arbitrary IDs (403 account_not_granted), and rejects workspace/account currency mismatch (409 currency_mismatch). Stores account name/currency/timezone and rotates generation so in-flight work on the old selection cannot import.

### POST /sync

OWNER only. Request {"date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD"}; max91 days inclusive. Sync flag required. Returns:
{
  "status": "SUCCEEDED",
  "campaigns_seen": integer,
  "metrics_seen": integer,
  "campaigns_created": integer,
  "metrics_created": integer,
  "metrics_updated": integer,
  "date_from": date,
  "date_to": date,
  "currency": string,
  "timezone": string,
  "workspace_timezone": string,
  "last_synced_at": ISO datetime,
  "reach_measure": "not_imported"
}
metrics_updated counts existing provider-owned daily rows processed, including identical rows on replay. No Meta orders/revenue/profit are imported. UI should label provider account timezone for the date interval and should not claim unique reach.

Failure format: HTTP409 (or403/422 as specified), {"detail":{"code": string,"message": safe string}}. Relevant codes: sync_disabled, invalid_date_range (422), connection_not_ready, account_selection_required, connection_changed, currency_mismatch, manual_spend_conflict, import_conflict, invalid_provider_data, credential_unavailable, RATE_LIMITED, TOKEN_EXPIRED, TOKEN_INVALID, PERMISSION_MISSING, NETWORK_ERROR, MALFORMED_RESPONSE, UNKNOWN_ERROR. Provider credential/permission failures durably set reconnect status; rate limits retain connection and permit a later manual retry. Import is atomic: a manual conflict returns no partial spend import.

### POST /disconnect

OWNER only. No body. Returns status fields plus disconnected: true. Clears only this workspace's Ads credential/selection and invalidates pending OAuth/generation. Never revokes shared Meta permissions or touches Instagram tokens.

### Legacy paths

/discovery/accounts, /discovery/campaigns and /sync/preview remain synthetic/mock-only when MOCK_ONLY; a CONNECTED live connection gets use_live_accounts instead of fake data. /staging/validate-read-only no longer silently creates a fake live client. Existing explicit injected synthetic tests and CSV/manual flows remain available.

## Setup environment names only

- META_ADS_APP_ID
- META_ADS_APP_SECRET
- META_ADS_OAUTH_REDIRECT_URI
- META_ADS_OAUTH_FRONTEND_CALLBACK_URL
- META_ADS_API_VERSION
- META_ADS_LOGIN_CONFIG_ID (optional)
- META_CONNECTIONS_ENABLED
- META_LIVE_OAUTH_ENABLED
- META_TOKEN_STORAGE_ENABLED
- META_TOKEN_ENCRYPTION_KEY
- META_SYNC_ENABLED

Dedicated Ads app credentials are required. Legacy Instagram/shared callback variables are not fallback values. Current reviewed Marketing version is v26.0; explicit earlier/unreviewed versions fail readiness. Exact callback matching, consent, optional business-login config and ingress-log requirements are documented in docs/meta-ads-live-setup.md.

## Persistence and business safety

- Workspace row locking serializes all Ads mutations across processes, including initial connection creation. State delete-returning prevents concurrent replay.
- Network calls occur outside long write transactions. Connection ID, generation and selected account are reread under the workspace lock before imports, selections and OAuth completion.
- Sync locks relevant campaign/metric rows; partial unique identity indexes and existing campaign/date uniqueness provide duplicate protection.
- External identity and normalized name/platform overlaps protect manual/CSV/archived data. Conflicts roll back the complete import.
- Only spend/impressions/clicks/canonical conversation-start messages and external campaign metadata are changed. CRM leads/orders/revenue/net_profit and reach are untouched.
- Account currency is checked against workspace before selecting and again before importing; row currency is verified too. Both timezone labels are returned.
- Daily query uses JSON-encoded time_range, time_increment1, campaign level. Maximum50 pages ×100 records per edge. Only validated after cursors are followed; arbitrary next URLs are ignored. No immediate retry storm.
- Critical connection/selection/sync events are persisted in AuditLog with safe details. No raw credentials or fingerprint are returned.
- No automatic schedule and no long-lived exchange: actual token expiry requires reconnect.

## Checks and exact commands

All commands ran through RDC on btc-radar in the assigned worktree. Values below are deliberately synthetic disposable test settings, not deployed credentials.

Full backend final run:
```sh
docker run --rm --network none --entrypoint python -e DATABASE_URL=sqlite+pysqlite:///:memory: -e JWT_SECRET=sellora-controlled-test-secret-at-least-32-chars -e SECRET_KEY=sellora-synthetic-tests-only -v /home/btcradar/commander-workspaces/sellora-migration/release-reconcile-20261020/backend:/app:ro -v /home/btcradar/commander-workspaces/sellora-migration/release-reconcile-20261020/deploy:/deploy:ro -v /home/btcradar/commander-workspaces/sellora-migration/release-reconcile-20261020/.gitignore:/.gitignore:ro -v /home/btcradar/commander-workspaces/sellora-migration/release-reconcile-20261020/frontend/src:/frontend/src:ro -w /app sellora-backend:16f1946ac1b6b858c49ded8bb9a5224d0da0d807 -m pytest -q -p no:cacheprovider tests
```
Result:646 passed,30 skipped,5 warnings in14.58s. Skipped tests require their explicitly isolated PostgreSQL or other integration fixture. Existing deprecation/collection warnings only.

Clean disposable migration replay:
```sh
docker exec sellora-integrations-qa-pg-20261020 createdb -U sellora_qa sellora_ads_final
docker run --rm --network sellora-integrations-qa-20261020 --entrypoint python -e DATABASE_URL=postgresql+psycopg://sellora_qa:synthetic-integrations-qa-only@sellora-integrations-qa-pg-20261020:5432/sellora_ads_final -e SELLORA_DISPOSABLE_DATABASE=1 -e JWT_SECRET=sellora-controlled-test-secret-at-least-32-chars -e SECRET_KEY=sellora-synthetic-tests-only -v /home/btcradar/commander-workspaces/sellora-migration/release-reconcile-20261020/backend:/app:ro -w /app sellora-backend:16f1946ac1b6b858c49ded8bb9a5224d0da0d807 -m alembic upgrade head
```
Result: fresh schema upgraded through all39 migrations to202610200039. Container/network are the parent's named private disposable resources; new DB lives only inside that tmpfs PostgreSQL container.

Final PostgreSQL gate plus transport:
```sh
docker run --rm --network sellora-integrations-qa-20261020 --entrypoint python -e DATABASE_URL=postgresql+psycopg://sellora_qa:synthetic-integrations-qa-only@sellora-integrations-qa-pg-20261020:5432/sellora_ads_final -e SELLORA_DISPOSABLE_DATABASE=1 -e JWT_SECRET=sellora-controlled-test-secret-at-least-32-chars -e SECRET_KEY=sellora-synthetic-tests-only -v /home/btcradar/commander-workspaces/sellora-migration/release-reconcile-20261020/backend:/app:ro -w /app sellora-backend:16f1946ac1b6b858c49ded8bb9a5224d0da0d807 -m pytest -q -p no:cacheprovider tests/integrations/meta_instagram/test_direct_lead_postgres.py tests/security/test_session_security_postgres.py tests/test_meta_ads_live_postgres.py tests/test_meta_ads_live_transport.py
```
Result:47 passed,4 warnings in5.39s. Covers real database replay/concurrency, independent sessions, duplicate sync, manual preservation, isolation, account/currency, actual OWNER HTTP flow, stale disconnect/account-switch, rate limit/expiry durability, and rejected destructive auth downgrade with unchanged current head.

After the final callback middleware no-store/no-referrer hardening:
```sh
docker run --rm --network none --entrypoint python -e DATABASE_URL=sqlite+pysqlite:///:memory: -e JWT_SECRET=sellora-controlled-test-secret-at-least-32-chars -e SECRET_KEY=sellora-synthetic-tests-only -v /home/btcradar/commander-workspaces/sellora-migration/release-reconcile-20261020/backend:/app:ro -w /app sellora-backend:16f1946ac1b6b858c49ded8bb9a5224d0da0d807 -m pytest -q -p no:cacheprovider tests/test_meta_ads_oauth_access_log.py tests/test_meta_ads_live_transport.py tests/security/test_endpoint_inventory.py
```
Result:33 passed in2.44s. Actual Uvicorn loopback access logs tested for success and422; no external network.

git diff --check passed.

Earlier test iterations found obsolete live-state/fake-client expectations and missing read-only host mounts for three existing repository-file tests. These were corrected: mock tests now explicitly use MOCK_ONLY and cover the no-fallback boundary; full-suite harness mounts required repository files. No failing test was removed, skipped, or weakened to retain unsafe live behavior.

## Self-review and remaining limitations

Self-review closed the static mock-signing live-state flaw, disabled-default live client, query-string token transport, fake live fallback, missing pagination/daily encoding, overlapping messaging action counts, manual-name overlaps, missing stale-generation revalidation, missing CI PostgreSQL inclusion and public callback query logging. Exact inventory is231 routes/130 mutations; NP read-only OWNER entries and Meta OWNER/public-forward exceptions were reconciled.

The code has been exercised against synthetic provider transports and actual disposable PostgreSQL, not a real Meta app/account. Live app access review, correct Ads app credentials, provider consent and controlled owner-selected account validation remain prerequisites before activation. Marketing allowlist updates need an explicit support review. Large accounts/date ranges fail boundedly instead of partially importing. Upstream ingress logs also need query suppression before activation. Production database/flags and all working Instagram secrets were untouched.

Files changed: Meta clients/services/repository/models/schema/router, scoped callback redaction middleware and registration, additive039 migration, configuration, Meta tests, endpoint/security tests, CI PG gate and setup/inventory docs. Root-owned plan and Nova Poshta implementation files are excluded from the task commit.
