# Sellora Known Limitations for Pilot Users

Sellora is approved for a controlled guided MVP pilot. The following limitations remain and must be communicated before pilot shops rely on the platform for daily operations.

## External integrations not fully active

- Instagram Direct API ingestion is not connected.
- Meta Ads live OAuth, token storage, automatic synchronization and Conversions API are not active.
- Manual entry and CSV remain the supported advertising data sources.
- Nova Poshta real TTN creation and production status behavior require a separate controlled validation with a shop-owned credential.
- Nova Poshta background status synchronization is not enabled.
- Printable/downloadable TTN documents are not implemented.

## Commercial and onboarding scope

- Billing and subscriptions are not implemented.
- Unrestricted public self-service onboarding is not approved.
- Email invitations and password reset remain incomplete or outside the currently approved pilot scope.
- Organization-level super-admin capabilities are not part of the MVP pilot.

## AI and automation scope

- AI Direct parsing is not implemented.
- Predictive analytics and advanced AI recommendations are not implemented.
- Advertising guidance is deterministic and based on manual/imported data, not live Meta recommendations.

## Data and import boundaries

- Reports depend on the completeness of operational, manual and imported data.
- Import dry-run should be used before executing imports.
- Real business files must be sanitized before QA or support sharing.
- Passwords, tokens, API keys, full authorization headers, private customer exports and private spreadsheets must not be placed in feedback, screenshots, logs or issue comments.
- Deep advertising CSV import behavior remains a dedicated follow-up beyond the Sprint 8A.1 route/browser smoke.

## Inventory follow-up

Issue #134 tracks an edge case where archiving a product variant may leave a visible zero-stock inventory row.

Current impact:

- stock can be returned to zero;
- order reservation and inventory calculations passed the controlled-write E2E;
- the issue affects cleanup/visibility semantics rather than the verified commerce flow;
- it does not block the controlled pilot, but should be resolved before broader rollout.

## Shipment limitations

- Shipment drafts are pilot-ready.
- Real Nova Poshta provider actions were intentionally not called during Sprint 8A.1.
- TTN creation does not automatically complete an order; shipment and order statuses remain separate.
- TTN cancellation is not fully production-validated.
- Pilot users should use the Nova Poshta cabinet for printing until document generation is implemented.

## PWA and mobile limitations

- Browser/mobile QA passed at 375 × 812, 390 × 844, 430 × 932 and 768 × 1024.
- PWA installation on real iOS and Android devices remains a separate device-level validation.
- Offline caching of private CRM, finance, customer, order, workspace or token data is intentionally not enabled.

## Security and audit limitations

- Role authentication and representative tenant-isolation checks passed.
- Workspace A/B stale-data checks passed in browser QA.
- Audit logging is not yet standardized for every critical mutation.
- Pilot access should remain controlled, with explicit workspace memberships and least-privilege roles.
- Synthetic credentials used for QA should be rotated or removed after the testing window.

## Staging and deployment operational notes

Sprint 8A.1 resolved a Render incident where the Docker image could not locate Alembic revision `202607130021`.

The backend image now verifies the expected Alembic revision during build and startup. Runtime and packaged head both matched `202607130021` in the approved deployment.

Future deployment rules:

1. deploy from the approved `main` branch;
2. keep Render root directory and Docker build context aligned;
3. fail the image build when the expected revision is absent;
4. verify `/health` before browser or controlled-write QA;
5. rerun the same Sprint 8A.1 gate after migration, auth, tenant-isolation or core-flow changes.

## Sprint 8A.1 closure status

The following former blockers are closed:

- staging frontend access;
- backend health access;
- synthetic OWNER/MANAGER/ANALYST credentials;
- dedicated QA workspace;
- runtime Alembic verification;
- read-only gate;
- controlled-write E2E;
- browser/mobile QA;
- console/network review;
- workspace switching and stale-data validation.

Final result:

```text
Sprint 8A.1: APPROVED
Release decision: GREEN
Pilot scope: controlled and guided
```

## Sprint 4.2.3 Staging Access Limitation

- Staging QA remains blocked because the required staging frontend/backend URLs, secure credentials, controlled QA workspace, and role/permission confirmation were not provided.
- CSV template download, dry-run, execute import, duplicate import behavior, `/advertising`, Dashboard, Analytics, zero-denominator display, mobile, and theme checks remain unverified on deployed staging.
- Pilot readiness remains blocked until the deployed staging flow is completed with synthetic data only.

## Sprint 4.3 Advertising Insights Limitations

- Campaign insights are MVP decision support based on manual/CSV-imported aggregates for the selected period; they are not automated Meta recommendations.
- Decision statuses are frontend-computed and are not persisted backend enums.
- Top/weak campaign ranking depends on the quality and completeness of imported/manual metrics.
- Advertising import remains not pilot-ready while deployed staging QA is blocked.

## Sprint 4.3.1 Advertising Insights Validation Notes

- Decision statuses remain frontend-computed and non-persisted.
- NO_DATA campaigns are intended to appear in comparison only; they are not eligible for Top Campaigns because they lack enough advertising data.
- If frontend dependency installation is blocked by registry/proxy access, typecheck/build validation must be repeated in an approved dependency-cache environment.
- Advertising import remains not pilot-ready while deployed manual import staging QA is blocked.

## Sprint 4.3.2 Advertising Insights Validation Blockers

- The Sprint 4.3/4.3.1 advertising insights code still requires frontend build validation in an environment with approved npm dependency access; this environment cannot restore dependencies because the registry/proxy denies `@tanstack/react-query` and no lockfile is available for `npm ci`.
- `/advertising` browser QA, mobile widths, and dark/light theme verification remain pending until either dependencies are restored for a local browser run or secure staging access is provided outside the report.
- Backend runtime validation is limited to `compileall` here; `pytest` and FastAPI app import require backend dependencies that the Python package proxy currently blocks.
- This is an environment validation blocker, not a new advertising feature blocker: no backend/API enum values, deployment architecture, Meta Ads behavior, or persisted decision-status enums should be changed to work around it.

## Sprint 4.3.3 Frontend Dependency Reproducibility Blocker

- `frontend/package.json` is npm-based, but no authoritative `frontend/package-lock.json` exists yet; this prevents deterministic `npm ci` in CI and local validation environments.
- `npm install --package-lock-only` is blocked here by a registry/proxy `403 Forbidden` response for `@tanstack/react-query`; the lockfile must be generated from an approved npm registry/cache rather than hand-written.
- Until the lockfile exists and dependencies can be restored, frontend typecheck/build and local `/advertising` browser/mobile/theme QA remain environment-blocked.
- CI should treat `frontend/package-lock.json` as the future authoritative lockfile and should fail if it drifts from `frontend/package.json` once it is committed.

## Sprint 4.5 — Advertising reporting readiness limits

- `/advertising` is consolidated as an owner-facing MVP report for manual/CSV-imported ad metrics, campaign insights, manual attribution clarity, and pilot readiness status.
- The readiness block is informational and does not mark the advertising module production-ready.
- Advertising import remains not pilot-ready until deployed staging import QA passes with synthetic data.
- Sprint 4.4 manual attribution remains conditionally approved until PostgreSQL runtime migration QA and browser/mobile attribution QA are completed.
- Meta Ads API OAuth, automatic sync, and automatic attribution remain future work and are not active.

## Sprint 4.5.1 — Staging/runtime QA blocked

- Advertising pilot readiness cannot be claimed because staging frontend/backend URLs, secure test credentials, a controlled QA workspace, safe PostgreSQL test/staging DB access, migration window approval, and rollback/backup confirmation were not available in this environment.
- PostgreSQL runtime validation for `202607010015_manual_ad_attribution.py` remains blocked; do not run the Alembic upgrade/downgrade/upgrade sequence against production.
- Advertising CSV import, `/advertising`, `/leads`, `/orders`, order detail, workspace/cross-workspace, mobile, and theme QA remain blocked until staging/runtime inputs are provided.
- Advertising import remains not pilot-ready, and Sprint 4.4 remains conditionally approved until runtime and browser QA pass with synthetic data.

## Sprint 4.6 — Meta Ads readiness limitation

- Meta Ads API is planned and architecture-ready only; live OAuth, live API calls, token storage implementation, automatic sync jobs, automatic attribution, and Conversions API were not implemented.
- Manual entry and CSV import remain the current MVP advertising data source.
- Future Meta read-only sync must import delivery metrics only; Sellora orders, revenue, and profit remain internal business data unless a separate Conversions API sprint is legally/privacy reviewed.
- Future Meta OAuth must be OWNER-only, workspace-scoped, protected by state/CSRF validation, and store encrypted tokens without returning raw tokens to the frontend.
- Advertising import remains not pilot-ready and Sprint 4.4 remains conditionally approved until the existing runtime/staging blockers are closed.

## Sprint 4.7 — Fake Meta sync simulation limitation

- Meta Ads API is fake-client / simulation-ready / not active.
- The backend fake client, DTOs, mapper, and dry-run service use synthetic data only and do not perform live Meta API calls.
- No live OAuth, real token storage, production sync jobs, database migrations, automatic attribution, click tracking, or Conversions API were added.
- Manual entry and CSV import remain the current MVP advertising data source.
- Advertising import remains not pilot-ready and Sprint 4.4 remains conditionally approved until runtime/staging blockers are closed.

## Sprint 4.8 — Meta sync preview limitation

- Meta Ads API is fake-client + read-only DB comparison + sync preview ready / not active.
- Sync preview is dry-run only and performs no DB writes.
- Exact Meta identity matching remains future work because `external_source` / `external_campaign_id` fields are not persisted yet.
- Manual/CSV data is protected by default; overlap is flagged as `POTENTIAL_CONFLICT`.
- No live OAuth, live API calls, token storage, database migrations, sync-run persistence, production sync jobs, automatic attribution, click tracking, or Conversions API were added.
- Advertising import remains not pilot-ready and Sprint 4.4 remains conditionally approved until runtime/staging blockers are closed.

## Sprint 4.9 — External identity schema limitation

- Meta Ads API is schema design and sync persistence contract ready / not active.
- Exact Meta identity is still not persisted because Sprint 4.9 intentionally adds no database migration.
- Future safe writes require nullable external identity/source fields, manual/CSV backfill, workspace-scoped indexes, sync-run persistence, and PostgreSQL runtime QA.
- Manual/CSV data is protected by default; Meta-owned rows can update only Meta-owned rows with the same external identity.
- No live OAuth, live Meta API calls, token storage, DB writes for Meta sync, production sync jobs, automatic attribution, click tracking, or Conversions API were added.
- Advertising import remains not pilot-ready and Sprint 4.4 remains conditionally approved until runtime/staging blockers are closed.

## Sprint 4.10 — Runtime-gated migration draft limitation

- Meta Ads API is external identity schema draft prepared / runtime-gated / not active.
- The migration draft adds nullable external identity/source fields and non-unique lookup indexes, but PostgreSQL runtime migration QA is still required before full approval.
- No token storage, `meta_ad_connections`, live OAuth/API, production sync jobs, apply-sync, DB writes from Meta sync, automatic attribution, click tracking, or Conversions API were added.
- Source backfill is intentionally not guessed; unknown historical manual/CSV rows can remain null until safely classified.
- Advertising import remains not pilot-ready and Sprint 4.4 remains conditionally approved until runtime/staging blockers are closed.

## Sprint 4.11 — Meta Ads sync preview UX, feature gate, and admin review flow

Sprint 4.11 keeps Meta Ads API inactive and adds only UX, documentation, and regression coverage for a future review flow. The current active advertising source remains manual entry / CSV import, and advertising import is not pilot-ready until staging/runtime QA is completed.

### User-facing status and feature gate

- Frontend feature gate: `metaAdsSyncPreviewEnabled = false` by default.
- Current visible state: `NOT_ACTIVE` / `COMING_SOON` only.
- Meta Ads API is not active yet; there is no live OAuth route, no token input, no live Meta API call, no apply-sync button, and no production sync trigger.
- The disabled CTA says Meta Ads connection will be available in a future stage and cannot start OAuth or sync.

### Future sync preview UX labels

Display labels are frontend-only and must not become persisted backend/API enum values:

| Backend preview value | Ukrainian label | English label |
| --- | --- | --- |
| `WOULD_CREATE` | Буде створено | Will be created |
| `WOULD_UPDATE` | Буде оновлено | Will be updated |
| `WOULD_SKIP` | Без змін | No changes |
| `POTENTIAL_CONFLICT` | Потребує перевірки | Needs review |
| `NEEDS_EXTERNAL_ID_SUPPORT` | Потрібна підтримка Meta ID | Meta ID support needed |
| `INVALID` | Помилка в даних | Data issue |

### Future admin review flow contract

1. OWNER підключає Meta Ads у майбутньому етапі.
2. Sellora завантажує рекламні метрики у preview mode.
3. OWNER бачить, що буде створено, оновлено, пропущено або потребує перевірки.
4. Sellora не перезаписує ручні/CSV дані автоматично.
5. OWNER підтверджує тільки безпечні зміни у майбутньому apply-flow.
6. Sellora записує sync run після майбутнього підтвердженого запуску.

Sprint 4.11 does not implement steps 1, 5, or 6. Apply-sync, sync-run persistence execution, production sync jobs, token storage, and live OAuth remain future work.

### Manual/CSV protection

Sellora не перезаписує ручні або CSV-рекламні дані автоматично. Sellora does not automatically overwrite manual or CSV advertising data. Meta Ads provides spend, impressions, clicks, and messages where available; orders, revenue, and profit remain Sellora-side business data.

### Future UX states

Documented future states are `NOT_ACTIVE`, `COMING_SOON`, `PREVIEW_AVAILABLE`, `NEEDS_REVIEW`, `CONFLICTS_FOUND`, `READY_TO_APPLY`, `CONNECTED`, `SYNCING`, `SYNC_SUCCESS`, `SYNC_FAILED`, `TOKEN_EXPIRED`, `PERMISSION_MISSING`, and `DISCONNECTED`. Sprint 4.11 may only show `NOT_ACTIVE`, `COMING_SOON`, and feature-gated demo preview states; `CONNECTED`, `SYNCING`, and `SYNC_SUCCESS` remain future states and must not imply a live connection.

### Runtime-gated blockers remain

Sprint 4.10 runtime PostgreSQL migration QA remains skipped/pending, so Sprint 4.10 is not fully approved. Sprint 4.4 PostgreSQL runtime migration QA, advertising CSV import staging QA, browser/mobile/theme QA, and workspace/cross-workspace runtime QA remain open blockers.

## Sprint 4.12 — Meta Ads mock OAuth, RBAC contract, and token safety shell

Sprint 4.12 keeps Meta Ads API inactive and adds only a mock OAuth contract, OWNER-only service authorization checks, token redaction utilities, tests, documentation, and regression coverage. The current active advertising source remains manual entry / CSV import, and advertising import is not pilot-ready until staging/runtime QA is completed.

### Mock OAuth scope

- Mock authorization URL: `https://mock.meta.local/oauth/authorize`.
- Mock flow is service-only; no production route is exposed.
- No real Meta OAuth URL, real Meta permissions, live Meta API call, token persistence, database write, production sync job, apply-sync, or `meta_ad_connections` table is added.
- Mock state is generated server-side and includes `workspace_id`, `user_id`, `nonce`, `issued_at`, `expires_at`, and `purpose = meta_ads_mock_oauth`; it includes no token or secret.
- Real OAuth state persistence remains future work and must be workspace-scoped, user-scoped, expiring, and non-secret-bearing.

### OWNER-only RBAC contract

- OWNER may start the mock connect flow, validate the mock callback, and simulate disconnect.
- MANAGER may view status only and may not connect or disconnect.
- ANALYST remains read-only/no-connect and may not connect or disconnect.
- Frontend hiding is not the protection boundary; service-level authorization rejects non-OWNER roles.
- Workspace context must be validated server-side for future live routes.

### Token safety shell

- Token-like values are masked with `mock_token_************abcd` style output or a fully redacted value.
- Secret-like payload fields are redacted before safe reporting.
- Safe diagnostics use a short one-way fingerprint, not a token value.
- Raw token-like values must never be returned to frontend DTOs, stored, logged, included in audit payloads, or included in string/repr output.
- Encryption persistence is not implemented in Sprint 4.12.

### Mock connection DTO contract

Safe mock DTOs may include `status`, `provider`, `workspace_id`, `connection_mode = mock`, `authorization_url`, `state_expires_at`, `connected = false`, `requires_live_setup = true`, `token_stored = false`, `live_api_enabled = false`, `message`, and user-safe `issues`. They must not include raw token fields, real ad account IDs, real business IDs, real Meta user IDs, customer/order data, or secret fields.

### Future audit event contract

Future audit events are `meta_ads_connect_started`, `meta_ads_connect_completed`, `meta_ads_connect_failed`, `meta_ads_disconnected`, `meta_ads_token_refreshed`, and `meta_ads_permission_missing`. Audit records may include workspace/user context and outcome, but must never include raw tokens, client secrets, cookies, customer PII, or customer/order payloads. Sprint 4.12 does not add a new audit table.

### Runtime-gated blockers remain

Sprint 4.10 runtime PostgreSQL migration QA remains pending, so Sprint 4.10 is not fully approved. Sprint 4.4 PostgreSQL runtime/staging/browser QA blockers, advertising CSV import staging QA, browser/mobile/theme QA, and workspace/cross-workspace runtime QA remain open. Meta sync remains not active, and manual/CSV remains the MVP advertising source.

## Sprint 4.13 — Meta Ads mock API boundary, route RBAC, and audit stubs

Sprint 4.13 keeps Meta Ads API inactive while preparing a backend-only, mock API boundary for future OAuth testing. The mock route prefix is `/integrations/meta-ads/mock`; it is disabled by default through `META_ADS_MOCK_OAUTH_API_ENABLED=false` and does not require any secret to remain inactive.

Mock API contract:

- `GET /integrations/meta-ads/mock/status` returns a safe not-active status with `provider=meta_ads`, `connection_mode=mock`, `connected=false`, `token_stored=false`, and `live_api_enabled=false`.
- `POST /integrations/meta-ads/mock/oauth/start` is OWNER-only, works only when the mock API feature gate is enabled, and returns only the obvious mock URL `https://mock.meta.local/oauth/authorize`.
- `POST /integrations/meta-ads/mock/oauth/callback` is OWNER-only, validates signed mock state, rejects invalid/expired/mismatched state, masks and discards synthetic token-like values, and returns only token-safety metadata.
- `POST /integrations/meta-ads/mock/disconnect` is OWNER-only and returns a non-persistent mock disconnect acknowledgement.

Route-level RBAC mirrors the Sprint 4.12 service contract: OWNER may start/callback/disconnect in mock mode when explicitly enabled for tests/dev; MANAGER and ANALYST are denied connect-like actions. Status viewing remains read-only. Frontend hiding is not the only protection.

Audit event stubs are non-persistent DTOs only. They document future events such as `meta_ads_mock_connect_started`, `meta_ads_mock_connect_callback_validated`, `meta_ads_mock_connect_denied`, `meta_ads_mock_disconnected`, and `meta_ads_mock_status_viewed`; no audit table or migration is added. Stub payloads must not include raw tokens, client secrets, cookies, customer/order data, or live account identifiers.

Safety guarantees for this sprint:

- no live Meta OAuth was implemented;
- no facebook.com OAuth redirect or graph.facebook.com API call was added;
- no real Meta OAuth URL, token storage, token input field, `meta_ad_connections` table, database migration, apply-sync, DB write, or production sync job was added;
- manual entry / CSV import remains the active MVP advertising source;
- Meta sync remains not active;
- Sprint 4.12 remains conditionally approved until frontend dependency recovery and browser/mobile QA are completed;
- Sprint 4.10 runtime PostgreSQL migration QA remains pending;
- Sprint 4.4 PostgreSQL runtime/staging/browser QA blockers remain open;
- advertising import is not pilot-ready.

## Sprint 4.14 — Advertising 4.x freeze and Part 5 handoff

Advertising is feature-frozen for now. Advertising is architecture-ready and locally validated, but Advertising is not pilot-ready and Advertising import is not pilot-ready.

Final Advertising 4.x status: **Advertising 4.x — architecture-ready / locally validated / feature-frozen / not pilot-ready**.

Meta Ads status: **Meta Ads API — mock/future-ready / not active**.

Manual/CSV remains the active source. Meta Ads API remains not active. Live OAuth/token storage/apply-sync are future work. Runtime/staging blockers are tracked separately in `docs/advertising-known-blockers.md`.

Part 5 may use Advertising data only as conditional manual/CSV source. Finance 5.x must not depend on live Meta OAuth, token storage, automatic attribution, apply-sync, production sync jobs, or unresolved runtime/staging QA.

Sprint 4.10 runtime PostgreSQL migration QA remains pending. Sprint 4.11 browser/mobile/theme QA remains pending. Sprint 4.12 browser/mobile QA remains pending. Sprint 4.4 PostgreSQL runtime/staging/browser QA blockers remain open.

## Finance 5A known limitations

Finance 5A is not full бухгалтерія and does not include bank statement import, payment gateway reconciliation, tax accounting, or a complete expenses ledger.

Finance uses Advertising data only as conditional manual/CSV source until Advertising runtime/staging blockers are resolved.

Meta Ads API is not active.

Discount fields are not available in the current finance schema, and cancelled/returned/refunded orders are excluded from revenue to avoid double-counting refunds. Shipment costs may be incomplete if shipment data is missing.

## Finance 5B known limitations

Manual finance adjustments improve profit accuracy but are owner-entered and may be incomplete. They are not a full accounting ledger and do not include tax reporting, bank import, payment gateway reconciliation, payroll, invoices, or fiscal receipts.

The `finance_adjustments` migration requires safe PostgreSQL runtime QA before production migration approval.

Advertising data remains a conditional manual/CSV source until runtime/staging blockers are resolved.

Meta Ads API is not active.

## Epic Sprint 5C — Finance stabilization limitations

- Finance adjustments migration has passed static Alembic chain validation, but PostgreSQL runtime migration QA remains pending until tested against a safe staging/test database.
- Browser/mobile QA for `/finance` remains pending when Playwright or staging browser access is unavailable; static regression scripts are not screenshot QA.
- Sellora Finance is operational profit analytics, not full accounting or tax reporting.
- Advertising data remains a conditional manual/CSV source until runtime/staging blockers are resolved.
- Meta Ads API is not active, and Part 6 Meta API work will be handled in separate dedicated sprints.

## Sprint 6A — Meta API readiness limitations

Meta Ads API is not active.

Sprint 6A prepares setup, security, OAuth, token storage, and QA design only. No live OAuth, no token storage, no live API calls, no real Meta app credentials, no real ad account data, no `meta_ad_connections` migration, and no production sync were implemented.

Advertising remains feature-frozen and not pilot-ready. Finance 5.x remains locally validated with runtime migration QA and browser/mobile QA blockers tracked separately.

## Sprint 6A.1 — legal and staging prerequisites limitations

Meta Ads API is not active.

Sprint 6A.1 prepares legal URLs, staging URL inventory, Meta App input pack, OAuth redirect URI planning, and environment variable planning only. No live OAuth, no token storage, no live API calls, no production sync, and no `meta_ad_connections` migration were implemented.

Legal pages are MVP drafts and require legal review before production launch, payment activation, or Meta App Review submission. Staging URL values remain placeholders until real public staging URLs are supplied.

## Sprint 6B — Meta encrypted connection foundation

Sprint 6B adds encrypted token storage infrastructure and connection records behind feature gates.

Meta Ads API is not sync-active.

Live sync, scheduled jobs, apply-sync, and Conversions API are not implemented.

Real OAuth validation requires staging URLs, legal review, Meta App setup, and safe PostgreSQL runtime migration QA.

Advertising remains feature-frozen and not pilot-ready.

## Sprint 6C — Meta read-only discovery and sync-preview foundation

Sprint 6C adds read-only discovery and sync-preview foundations only.

Meta Ads API is not sync-active.

No scheduled sync jobs, no apply-sync, no ad_metrics writes, no customer/order data transfer, and no Conversions API were implemented.

Manual/CSV remains the active Advertising source.

Advertising remains feature-frozen and not pilot-ready.

Runtime/staging validation is still required before any live sync claim.

## Sprint 6D — Live read-only Meta foundation and staging validation gate

Sprint 6D adds live read-only client foundation and staging validation gate only.

Meta Ads API is not sync-active.

No scheduled sync jobs, no apply-sync, no ad_metrics writes, no ad_campaigns writes, no customer/order data transfer, and no Conversions API were implemented.

Manual/CSV remains the active Advertising source.

Advertising remains feature-frozen and not pilot-ready.

Real staging OAuth validation, runtime migration QA, Meta App setup, legal review, and browser/mobile QA are still required before pilot-ready claims.

## Sprint 6E — Runtime/Staging QA gate

Sprint 6E is a QA/risk-closure sprint for the existing Meta Ads foundations.

Result: **BLOCKED** because confirmed safe non-production PostgreSQL runtime migration QA, real Meta OAuth staging validation, Meta Developer App setup, legal review, staging URLs, role-specific test accounts, safe connected workspace validation, and browser/mobile staging smoke QA were unavailable.

Meta Ads API is not production sync-active. Advertising remains feature-frozen and not pilot-ready. No scheduled sync jobs, no apply-sync, no ad_metrics writes, no ad_campaigns writes, no customer/order data transfer, and no Conversions API were implemented.

## Sprint Admin Roles & Users limitations

- Email invitations are not implemented.
- Password reset is not implemented in this sprint.
- Force password change is not implemented.
- User profile editing is not implemented.
- Billing/plans are not implemented.
- Organization-level super admin is not implemented.
- Audit log UI is not implemented.
- Reactivation of inactive workspace user is future work.

## Sprint 7A pending QA

- Staging runtime QA must be completed from an environment that can reach the Vercel and Render staging URLs.
- PostgreSQL runtime migration QA for `202607050019_admin_roles_users` remains pending on a safe non-production database.
- Manual mobile checks at 375px, 390px, 430px, and 768px remain required.

## Sprint 7A.1 staging QA blocker

Manual staging QA for OWNER, MANAGER, ANALYST, workspace switching, team management, mobile More sheet, data isolation, and runtime migration remains blocked in this container because staging URLs return proxy `CONNECT tunnel failed, response 403`.

## Sprint 7F runtime migration blocker

Runtime PostgreSQL migration QA remains blocked in this container by database host resolution failure. No schema mutation was executed; retry from a network that can resolve and reach the safe non-production PostgreSQL host.

## Sprint 7B core flow limitations

Lead conversion links and customer-specific order history remain future UX improvements unless supported by existing endpoints/routes. Manual browser QA at 375px, 390px, 430px, and 768px remains recommended. No database migration was added in Sprint 7B.

## Sprint 7C dashboard limitations

Dashboard owner experience now has clearer KPI, funnel, advertising, finance, inventory, alert, and recent-order explanations. Remaining limitations: manual mobile/browser QA is still recommended, Sprint 7F runtime migration QA remains blocked, and Instagram message counts are not shown because live messaging integration is out of scope. No database migration was added in Sprint 7C.

## Sprint 7D mobile/PWA limitations

Service worker/offline support is deferred because Sellora handles private business data and must not cache API responses, customer/order records, finance data, advertising data, workspace data, or tokens. PWA install behavior still needs manual testing on real iOS/Android browsers. No database migration was added in Sprint 7D.

## Sprint 7E security QA limitations

Sprint 7E added automated RBAC and tenant-isolation coverage for shared guards and representative high-risk flows, but it does not replace manual browser/mobile security QA for route flashes, workspace-switch race conditions, and role-specific navigation behavior.

Audit logging is reviewed but not fully standardized for every critical mutation. Expanding audit schema or persistence semantics is deferred because Sprint 7E does not allow new migrations.

Sprint 7F runtime PostgreSQL migration QA remains blocked separately and is not resolved by Sprint 7E.

## Sprint 7E.1 closure limitations

- Browser-level workspace-switch race-condition QA is still recommended for staging, but static regression proof and query-cache hardening are now in place.
- Audit logging is not claimed complete; missing/partial events are registered in `docs/security-audit-logging-backlog.md` for a future approved hardening sprint.
- Sprint 7F Runtime Migration Closure remains blocked until a safe PostgreSQL runtime environment is available; do not run production migrations to close it.

## Sprint 8A staging release gate limitations

- Sprint 8A staging execution is blocked in this container by proxy `CONNECT tunnel failed, response 403` for both the Vercel frontend and Render backend URLs.
- Secure synthetic OWNER/MANAGER/ANALYST staging credentials were not available, so authentication, role, workspace and controlled-write gates were not executed.
- The synthetic Lead → Customer → Product/Variant → Inventory → Order flow was not executed and must be rerun from an allowed staging network.
- Sprint 7F runtime PostgreSQL migration QA remains blocked separately; Sprint 8A does not resolve database runtime compatibility.
- Nova Poshta real validation, Import deep QA, Finance deep QA and Advertising deep QA remain assigned to later Phase 8 sprints.

## Sprint 8A.1 staging E2E closure limitations

- Staging access remains blocked by proxy `CONNECT tunnel failed, response 403`; no app-level frontend/backend response was observed.
- Secure synthetic role credentials and dedicated QA workspace ID remain unavailable in this environment.
- Runtime Alembic revision is unknown; Sprint 7F remains separately blocked and no migration was executed.
- Controlled-write E2E, workspace-switch runtime isolation, cross-workspace staging negatives, browser/mobile QA and console/network review remain pending.

## Sprint 8B limitations

First-run guidance and demo workspace generation are implemented for controlled guided pilots. Public self-service onboarding, billing, live Instagram/Meta integrations, real Nova Poshta TTN validation, Import Center deep QA, Finance deep QA and Advertising deep QA remain future sprint scope.

## Sprint 8C import limitations

- Import Center hardening does not add background jobs, public file storage, AI mapping, Google Sheets sync, Meta live sync, or Nova Poshta TTN creation.
- Durable dry-run token persistence would require a schema change; Sprint 8C records an audit signature and revalidates on execute without adding a migration.
- Staging import gates, 100/1,000 row benchmarks, and browser/mobile import QA remain required before full Sprint 8C approval.
- Issue #134 remains a focused QA item for archived variants and zero-stock inventory rows.

## Sprint 8D operations limitations

- Real Nova Poshta TTN creation and delivery synchronization remain out of scope until Sprint 8E.
- Finance/profit deep validation remains Sprint 8F.
- Last-unit concurrency needs runtime PostgreSQL/staging evidence before full Sprint 8D approval.
- Browser/mobile staging evidence and QA8D cleanup evidence remain required before final approval.
