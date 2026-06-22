# Meta Ads Integration Plan — Future Work

Sprint 4.0 prepares Sellora for Meta Ads data flow, but automatic Meta Ads API sync is not active yet. Manual advertising import remains the MVP path.

## Future connection flow

1. OWNER opens `/settings/integrations` and starts Meta Ads connection.
2. Sellora redirects through official Meta OAuth.
3. Meta returns an authorization code to the backend callback.
4. Backend exchanges the code server-side and stores encrypted tokens in workspace-scoped integration credentials.
5. UI displays only masked connection state, never raw tokens.
6. OWNER selects an ad account that belongs to the connected business.
7. Scheduled sync imports campaigns, ad sets, ads, and daily insights.

## Required Meta assets and permissions

Future implementation will require a reviewed Meta app, business assets, a redirect URI, and least-privilege permissions for ad account insights. Exact permissions must be validated against current Meta platform requirements during the implementation sprint.

Do not commit real Meta app IDs, app secrets, access tokens, business IDs, ad account IDs, campaign IDs, customer data, or screenshots containing private account data.

## Data model mapping

| Meta concept | Sellora target |
| --- | --- |
| Ad account | Workspace-scoped integration connection / future ad account table |
| Campaign | Existing `AdCampaign` with future external campaign mapping |
| Ad set | Future additive table or external adset mapping field |
| Ad | Future additive table or external ad mapping field |
| Daily insights | Existing `AdMetric` daily rows |
| Attribution | Future lead/order campaign mapping fields |

Sprint 4.0 does not add destructive schema changes. Future fields such as `external_account_id`, `external_campaign_id`, `external_adset_id`, `external_ad_id`, `source`, `sync_status`, `last_synced_at`, and `currency` should be additive and workspace-scoped.

## Sync design

- Sync should fetch daily insights by date range and paginate safely.
- Rate limits should use retries with backoff and a workspace-level sync status.
- Sync must be idempotent by workspace, platform, external campaign/adset/ad identifiers, and metric date.
- Raw third-party payloads should not be stored unless explicitly reviewed and sanitized.
- Manual/imported data must remain available if Meta sync fails.

## RBAC and workspace isolation

- OWNER manages connection and token rotation.
- MANAGER may view/import campaign metrics if allowed by existing workspace role policy, but should not manage Meta credentials.
- ANALYST may view advertising analytics where current rules allow, but cannot manage credentials.
- Workspace A must never see or use Workspace B Meta credentials, ad accounts, campaigns, metrics, or attribution mappings.

## Known limitations

- Automatic Meta Ads API sync is not active in Sprint 4.0.
- Instagram Direct, message parsing, AI attribution, billing, and scraping are out of scope.
- Manual advertising import remains the safest MVP fallback until OAuth, sync jobs, rate limits, and token refresh are fully implemented and tested with fake clients in automated tests.

## Manual fallback

If Meta Ads API sync is unavailable, revoked, rate-limited or not approved yet, Sellora must continue to support manual fallback through spreadsheet import and manual daily metric entry.

## Sprint 4.0.1 validation status

The Meta Ads readiness UI remains a placeholder only. Automated validation confirms the placeholder and documentation markers are present, but no real Meta OAuth, token exchange, ad account connection, or API sync was executed. Manual staging QA must verify that users are not misled into thinking Meta Ads automation is active.
