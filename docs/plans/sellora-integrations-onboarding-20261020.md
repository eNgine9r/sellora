# Sellora integration onboarding — 2026-10-20

## Spec and scope
User approved finishing Nova Poshta onboarding and Meta Ads OAuth/account selection/read-only provider sync before any controlled real sale. Existing runtime release debd301 (backend byte-equivalent to16f1946). Worktree branch codex/2026-10-20-integrations-onboarding, base debd301567b57c18ed2e16ce8321f94d4c089d14. Do not repeat completed Direct release QA except relevant regression.

## Global Constraints
- Preserve all working data, orders, messages, Instagram tokens and production hotfixes.
- No real customer messages, real orders, real TTN, provider campaign/budget writes or credential rotation.
- Do not connect or probe saved credentials without safe scope; use synthetic provider transports for development.
- No production DB migration, feature activation or deployment by implementer agents; root owns rollout.
- All connection and sync operations workspace-scoped with backend OWNER permission; no secret values in UI/logs/reports.
- Provider-specific clients, services, repositories and thin API routes; Ukrainian UI and English backend enum values.
- Production Alembic head is202610200038. Any new migration must extend038 and be additive; load supabase-postgres skill before DB changes.
- Run meaningful provider/persistence/RBAC/replay/isolation tests. Keep legacy mock/CSV flows compatible and never present mock data as live.
- No subagents dispatched by implementers; root owns task and final reviews. Never modify unrelated services or branch history.
- Agent commits only named task files with per-command git identity Sellora AI Agent / sellora-ai-agent@users.noreply.github.com. No push or deployment by agents.
- Use Remote Desktop Commander btc-radar device9321d14a-8403-405b-ae6b-662323be0e82. Host has no rg; Python/git file search acceptable.
- Test backend without live credentials/network: docker run --rm --network none --entrypoint python -e DATABASE_URL=sqlite+pysqlite:///:memory: -e JWT_SECRET_KEY=sellora-controlled-test-secret-at-least-32-chars -v /home/btcradar/commander-workspaces/sellora-migration/release-reconcile-20261020/backend:/app:ro -w /app sellora-backend:16f1946ac1b6b858c49ded8bb9a5224d0da0d807 -m pytest -q -p no:cacheprovider <test paths>.
- Root baseline55 NovaPoshta/MetaOAuth tests passed. Existing frontend/node_modules symlink reuses dependencies; no dependency install needed if valid.

## Task 1: Nova Poshta account onboarding
Read AGENTS.md and this task. Own NP-specific backend/frontend tests plus settings integration wiring and UA/EN translation keys required by this task.
Implement a simple localized onboarding flow:
1. Explain official one-time key connection; link directly to official business-cabinet security/settings page (verify official link). Do not claim OAuth/phone-login support.
2. Key input is password, never saved in browser storage or reflected raw. Preserve existing key when blank.
3. Add bounded read-only authenticated provider lookup APIs for sender counterparties and their contacts. Select sender, contact, city and warehouse from names; no technical Ref UUID entry in normal UI. Only OWNER may manage credentials/lookups.
4. Provider lookups must never create counterparties, contacts or InternetDocuments. Validate selected tuples with existing gates.
5. Verify access and sender setup with existing test-connection route; show concrete next action for missing key/sender/verification/write permission. Keep explicit workspace TTN permission disabled by default. No write permission enabled automatically by wizard.
6. Preserve existing settings and shipment behavior. Sender selection changes invalidate contact/verification appropriately.
7. Cover actual request shapes and safe errors, arbitrary sender access rejection, RBAC/isolation, blank-key behavior, failed lookup, desktop/mobile flow using synthetic provider data. Add browser fixture or meaningful existing regression integration as appropriate.
Report includes changed files, commands/results, remaining activation prerequisites. Commit task.

## Task 2: Meta Ads secure OAuth and provider sync backend
Read AGENTS.md and this task. Own Meta Ads backend models/migrations/services/clients/routes/tests/config only. Reuse Task1 interfaces unchanged.
Finish real OAuth foundation; do not just flip flags. Existing DisabledMetaLiveOAuthClient is default and existing state signature is static mock key; both unsafe/incomplete for live use.
1. Server-only official Facebook Graph token exchange, verify granted ads_read permission, and optional supported long-lived exchange; HTTPS official hosts, bounded timeouts, no token URL/log leakage, safe provider errors, no redirect-following to arbitrary hosts.
2. Live state uses unpredictable server-held single-use state, bound to initiating OWNER/workspace, expiration, atomic replay protection with persistence suitable for multi-process restart; mock state retains mock-only boundary. Any additive migration extends038. Connect/reconnect/disconnect audit persists. Disconnect clears only the scoped Ads credential locally; do not revoke shared Meta app permissions or touch Instagram tokens.
3. Facebook Login for Business configuration supported if needed; ads_read least privilege. Separate Ads callback configuration from working Instagram callback; never alter Instagram secret/token paths. Use dedicated META_ADS_OAUTH_REDIRECT_URI, META_ADS_OAUTH_FRONTEND_CALLBACK_URL and META_ADS_API_VERSION configuration. Existing META_OAUTH_REDIRECT_URI and META_OAUTH_FRONTEND_CALLBACK_URL point to Instagram on production and must not be reused/changed. Meta Ads default should be supported Marketing API v26.0 (official release2026-07-29), not legacy defaultv20.0. Graph and Marketing version lifetimes differ; do not infer Marketing support from Graph version table. Explicit deprecated version must fail readiness. App credentials can be explicitly configured for Ads using dedicated optional aliases if appropriate; do not assume the current Instagram app grants ads_read.
4. Real account discovery and explicit selection validated against accounts granted by provider for this token. Never default silently to first account or accept arbitrary external account IDs. Return account IDs (non-secret identifiers) only in authenticated scoped selection API; never tokens.
5. Live read-only Graph client must paginate safely via validated cursors (never arbitrary next URL), fetch daily time_increment1 with correctly encoded time_range, avoid double-counting message action types, handle rate limits/expiry safely, finite bounded page/date limits.
6. Manual sync endpoint imports campaigns and daily delivery metrics idempotently by workspace/account/external campaign/date. No Meta writes, no customer/order data sent. Protect concurrent sync via DB locking/constraints. Manual/CSV conflicts must be explicit and not overwritten. Existing preview_service.py already detects external identity and name/platform manual overlaps; use equivalent protection in live import so same-name manual campaign data is not silently duplicated as new Meta spend. Preserve existing Sellora order/revenue/profit attribution data; Meta metrics cannot fabricate orders/revenue/profit. Money currency/timezone visibly retained and mismatched workspace currency handled explicitly. Reach not summed across days as unique reach; if shared summaries sum daily reach, clearly expose that measure as sum of daily reach or omit unique-reach claim.
7. Durable last success/failure, clear reconnect errors and audit. Fetch provider data outside long DB write transactions where possible. No periodic schedule until manual sync is proved.
8. Old preview/mock endpoints remain explicitly synthetic; never let connected live route fall back to FakeMetaAdsReadOnlyClient.
9. Safe status response exposes implemented/configuration/capability blockers; no secret/fingerprint needed in new UI.
Tests include state tamper/expiry/replay/cross-user/workspace, actual OWNER routes, token redaction/transport, account permission validation, pagination, daily query encoding, retry/rate limit, expired token, duplicate/concurrent import, manual conflict preservation, no order/customer data transfer. Use isolated Postgres when necessary and load DB skill first. Wire new disposable-Postgres tests into the existing GitHub CI PostgreSQL job (it currently runs explicit file lists). Existing tests/security/test_session_security_postgres.py hardcodes head038: update it to verify recovered security ancestors and unchanged current head after rejected downgrade, preserving the destructive-downgrade guard rather than removing the test.
Report exact new frontend API contracts and activation env names (names only). Commit task.

## Task 3: Meta Ads connection and sync UI
Read AGENTS.md and this task. Own MetaAds-specific frontend, integration wiring, UA/EN keys, browser fixtures/tests. Consume Task2 actual API contracts; never invent successful connected state.
1. Replace coming-soon card with runtime-aware setup/blocker status and OWNER connect action when backend ready.
2. OAuth returns to separate MetaAds callback page. Bind pending state/workspace in session memory/sessionStorage only (never tokens); validate callback via backend with current actor. Clear code/state URL immediately, keep app referer privacy, handle denial/expiry/error/logout/workspace switch. Callback POST must run once under React StrictMode and recover deterministic status after accidental repeats.
3. Explicit ad-account name/currency/timezone picker; disconnect action with confirmation; no automatic first-account selection.
4. Manual date-range sync with clear data source and last sync/error state; explain Meta spend/delivery vs Sellora sales/profit. Date window bounded by backend. Disable duplicate submissions and permissions.
5. Loading/empty/error/config missing/reconnect/no accounts states, desktop/mobile accessibility and localization.
6. Real browser synthetic session test exercises connect/callback/select/sync/repeat/conflict/error/RBAC/isolation navigation; never call real provider or real data mutation.
Run typecheck/lint/build and scoped browser/static tests. Commit task.

## Task 4: Integrated QA and release preparation
Root coordinates broad review, final fixes by implementer, full CI and release notes/rollback.
- Check migration chain and clean DB +038 upgrade on disposable Postgres; no production migrations until verified and independently reviewed.
- Full backend regression, browser desktop/mobile and cookie auth integration.
- No real credentials/provider canary claims. Saved NP keys and Meta developer app consent/App Review may need owner action; report exact blocker.
- New code can be staged with features fail-closed if activation missing. Preserve exact old backend image and env/volume; additive schema compatible rollback only.
- Update stale integration docs to accurate delivered state with setup and non-secret operational steps.
