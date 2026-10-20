# Meta Ads read-only setup

The implementation is feature-gated and does not activate itself. Marketing API default is v26.0, released 2026-07-29; the current reviewed allowlist contains only that version. Earlier or unreviewed explicit Ads versions fail readiness. Graph and Marketing version lifetimes are different.

## Configuration names

Required dedicated Ads configuration:
- META_ADS_APP_ID
- META_ADS_APP_SECRET
- META_ADS_OAUTH_REDIRECT_URI
- META_ADS_OAUTH_FRONTEND_CALLBACK_URL
- META_ADS_API_VERSION

Optional Facebook Login for Business configuration:
- META_ADS_LOGIN_CONFIG_ID

Existing gates and encryption configuration:
- META_CONNECTIONS_ENABLED
- META_LIVE_OAUTH_ENABLED
- META_TOKEN_STORAGE_ENABLED
- META_TOKEN_ENCRYPTION_KEY
- META_SYNC_ENABLED

Legacy preview/mock gates remain separate. Do not reuse or change META_OAUTH_REDIRECT_URI, META_OAUTH_FRONTEND_CALLBACK_URL, META_GRAPH_API_VERSION, or Instagram credentials. The dedicated Ads app credentials are required; presence of an Instagram app does not establish Ads consent.

## Provider and callback setup

Register the dedicated Ads backend HTTPS callback ending in /api/v1/integrations/meta-ads/oauth/callback exactly in the Meta application. The authorization request and code exchange use precisely the same configured URI. Configure the frontend callback ending in /settings/integrations/meta-ads/callback separately. Both must be HTTPS without query or fragment; Instagram callback paths are rejected.

Use an Ads-capable app and the required Meta approval/access level for ads_read. The code verifies granted ads_read after exchange; it never requests ads_management. An optional Login for Business config ID is sent on authorization. No automatic long-lived exchange is performed; stored expiration is honored and reconnect is required on expiry.

The public GET callback only forwards code/state to the fixed configured frontend URL. It cannot connect or consume state. The frontend must immediately remove code/state from its browser URL, then use the current authenticated OWNER session and workspace to POST the code/state. Do not log these values, analytics URLs, or request payloads. The backend redacts this callback's query string from Uvicorn access logs before processing, including invalid requests. Any ingress/reverse-proxy access logs must also omit query strings for this callback before live activation.

## Read-only operation

After OAuth, the owner explicitly discovers and selects an account. IDs are returned only by the authenticated OWNER accounts API. Account selection re-fetches the granted list and rejects unavailable accounts and currency mismatch. No default first-account selection occurs. Account and workspace timezone labels are returned; daily rows use the provider account's timezone.

Manual sync is the only supported sync trigger. It is bounded to 91 days inclusive and 50 pages of at most 100 records each per endpoint. Pagination uses validated after cursors, never provider next URLs. Rate limits fail safely without immediate retries; a later manual retry is idempotent.

Campaigns and metrics retain external identity. A short database transaction locks the workspace and relevant rows; partial unique indexes additionally protect live external identity. Provider I/O happens outside that write transaction. Connection ID, generation and selected account are revalidated afterward; disconnect, reconnect or selection changes prevent stale results from being imported.

All-or-nothing import rejects manual/CSV identity and name/platform overlap, including archived/deleted existing identities. It updates only spend, impressions, clicks, conversation-start messages, and external campaign metadata. Sellora leads/orders/revenue/net profit remain untouched. Reach is deliberately not imported, avoiding a false unique-reach total. Campaign local operational status is initially PAUSED and objective OTHER; provider status/objective remain in their external fields.

No Meta campaign/budget writes, customer uploads, permission revocation or periodic jobs exist in this implementation. Disconnect only clears the workspace's local Ads credential and selections; Instagram credentials are untouched.

## Release evidence required

Run the full backend suite and PostgreSQL gate before release. Migration 202610200039 extends recovered 038 and adds OAuth state, generation/attempt columns and partial unique live identity indexes. No production migration or flags were changed during implementation. Live app approval, actual provider consent and a controlled owner-selected account sync remain deployment-stage validation, outside synthetic tests.


## Daily metric ownership

Advertising metric responses include source_type (nullable string) and provider_controlled_fields (string array). For source_type meta_live the array is exactly metric_date, spend, impressions, clicks, messages. The existing OWNER metric PUT rejects changed values in these fields with409 provider_metric_read_only and a fields array. Identical values remain accepted so existing full-form updates can still edit attribution. There is no implicit conversion to a manual override.

Reach is not imported by Meta sync and is not provider-controlled. Local reach, leads, orders, revenue and net_profit edits remain allowed and are preserved by later sync. Manual and CSV rows return an empty provider_controlled_fields array and retain existing editing behavior.

The callback middleware protects the canonical path and trailing-slash routing variants, including307 redirects and422 validation errors. The configured backend callback must target that route; unrelated HTTPS paths fail readiness. Migration039 explicitly removes PUBLIC/anon/authenticated table grants, including inherited TRUNCATE, while retaining backend owner/service-role access.
