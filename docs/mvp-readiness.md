# Sellora MVP Readiness — Sprint 2.7

## Ready for guided pilot testing

| Area | Status | Notes |
| --- | --- | --- |
| Core CRM flows | Pilot-ready | Leads, customers and order flow are available for guided testing. |
| Orders | Pilot-ready | Multi-item orders, statuses, payments and historical imports are available. |
| Products | Pilot-ready | Products, variants, categories and catalog import are available. |
| Inventory | Pilot-ready | Stock, reserved/incoming/minimum quantities and low-stock states are visible. |
| Analytics | Pilot-ready | Dashboard and Analytics reports use real/demo aggregate data. |
| Advertising manual metrics | Pilot-ready | Manual/imported historical ad metrics support spend, revenue and ROAS review. |
| Import Center | Pilot-ready with guidance | Dry-run, mapping, validation, row issues and duplicate warnings are available. |
| Demo dataset | Pilot-ready | Synthetic DEMO seed is idempotent and safe for demos. |
| Nova Poshta settings | Needs real API validation | Settings and shipment scaffolding exist; real API credentials need staging verification. |
| Localization | Pilot-ready | Ukrainian is primary; English is secondary. |
| Mobile UX | Needs pilot QA | Mobile-safe patterns exist; pilot checklist covers 375px/390px/430px/768px. |

## Known limitations

- Instagram Direct API is not connected yet.
- Meta Ads API is not connected yet.
- Billing/subscription system is not implemented yet.
- Full self-serve production onboarding is not implemented yet.
- Nova Poshta TTN behavior may require final validation with real settings/API key.
- AI Direct parser and predictive analytics are out of scope for this MVP phase.

## Next planned features after pilot feedback

1. Improve onboarding based on first-store behavior.
2. Expand import presets for common spreadsheet formats.
3. Harden Nova Poshta real-credential workflows.
4. Prioritize Instagram/Meta automation based on pilot pain points.
5. Add billing only after value and pricing are validated.

## Sprint 2.8 pre-MVP feedback readiness

- In-app feedback is available from the topbar with category, optional rating, message, current page and privacy hint.
- Feedback records are workspace-scoped in backend storage; owners/managers can review them in `/settings/feedback` and owners can update status.
- Pre-MVP release checks, known limitations and pilot release notes are documented for controlled external pilots.

## Sprint 2.9 readiness update — Mobile and list polish

- **Mobile sidebar footer:** compact profile row, aligned language/theme controls and compact logout are ready for pilot QA.
- **Mobile topbar:** secondary actions are consolidated behind a More menu on mobile so the primary order action stays reachable at 375px.
- **Date range selector:** custom period date inputs are mobile-stacked and native calendar indicators are styled for light/dark visibility.
- **Feedback modal:** feedback now uses the standard overlay modal/bottom-sheet pattern and keeps submit/cancel controls visible.
- **Reports navigation:** `/reports` is a stable alias to the existing `/analytics` reports experience to avoid duplicate report pages.
- **Orders pagination:** `/orders` defaults to 5 rows per page, supports 5 / 15 / 30 page sizes, and resets to page 1 when search, filters or sorting change.
- **Responsive QA focus:** verify 375px / 390px / 430px / 768px for dashboard, orders, products, inventory, analytics/reports, settings, feedback and sidebar drawer before pilot release.

### Sprint 2.9 follow-up checklist

- **Feedback modal positioning:** rendered through a viewport-level overlay so it is not clipped by the topbar/sidebar and remains usable as a bottom sheet on mobile.
- **Mobile More menu:** uses fixed viewport positioning with outside-click close behavior to avoid clipping and z-index conflicts.
- **Analytics pagination:** detailed sales rows on `/analytics` use the shared 5 / 15 / 30 pagination controls and reset when the local period changes.
- **Global period selector removal:** shared topbar no longer shows the duplicated period selector; local selectors remain on Dashboard and Analytics.
- **Topbar alignment:** visible topbar actions keep consistent height/alignment while avoiding unnecessary width changes.

## Sprint 3.0 readiness update — Nova Poshta production validation

- Nova Poshta credentials remain stored through the existing integration credential mechanism, are encrypted at rest, and are returned to the UI only as masked state.
- OWNER users manage Nova Poshta settings; MANAGER users can create and update shipments; ANALYST users remain read-only under the existing RBAC model.
- Sender settings now support saving/reloading without re-entering the credential, city/warehouse lookup, stale warehouse clearing after city change, and required-field validation before TTN creation.
- Shipment creation can be launched from order details and keeps order status independent from TTN creation.
- TTN creation stores tracking information on the shipment and prevents duplicate TTN creation for the same shipment.
- Safe localized errors are required for connection checks, city/warehouse search, TTN creation, and status sync; raw third-party payloads and secrets must not appear in UI or audit logs.
- Remaining future work: production validation with a controlled staging credential, background status synchronization, and fully validated TTN cancellation behavior.

## Sprint 3.1 readiness — Shipments and TTN

- Shipment list/detail UX now exposes order, customer, recipient, TTN, status and Nova Poshta context for pilot QA.
- TTN copy and status sync UX are available where tracking data exists.
- TTN printing/downloading remains a known limitation and is documented before broader pilot rollout.
- Order status and shipment status remain separate; TTN creation does not auto-complete orders.

## Sprint 3.2 readiness — Nova Poshta staging QA

- A dedicated staging validation checklist now covers credential, sender, recipient, TTN, status sync, RBAC, workspace, audit and mobile edge cases.
- Incomplete TTN responses and unavailable status sync are treated as safe failure states rather than confirmed shipment updates.
- Pilot readiness still requires manual staging validation with a controlled real credential before relying on Nova Poshta for daily operations.

## Sprint 3.2.1 readiness — Environment validation

- Backend test execution recovered locally: `compileall`, full `pytest`, and FastAPI app import pass.
- Frontend validation recovered locally: TypeScript typecheck and production build pass with available dependencies.
- Lint remains a known tooling follow-up because `next lint` prompts for initial ESLint configuration.
- Real Nova Poshta staging validation still requires a controlled API key and shop-approved test shipment; no fake validation is claimed.

## Sprint 4.0 readiness — Advertising integration foundation

- Manual advertising entry/import remains the active MVP path for spend, messages, leads, orders, revenue, ROAS, CPA and CPL.
- Meta Ads is presented as a preparation placeholder in integrations; automatic sync is future work and must not be represented as active.
- Advertising formulas and zero-denominator behavior are documented so `/advertising`, Dashboard and Analytics do not drift or render unsafe values.
- Future Meta Ads credential handling must be workspace-scoped, encrypted/masked, OWNER-managed and tested only with fake clients in automation.

## Sprint 4.0.1 readiness — Advertising validation recovery

- Backend validation is recovered locally: `compileall`, full `pytest` including advertising tests, and FastAPI app import pass.
- Frontend validation is recovered locally: TypeScript typecheck and production build pass for the Sprint 4.0 advertising placeholder and campaign-source UI.
- Regression coverage passes for the dedicated advertising foundation script and the full relevant frontend regression suite.
- Manual staging QA remains required before full Sprint 4.0 approval because no staging URL/credentials were available in this environment; do not claim fake Meta Ads or manual import validation.

## Sprint 4.1 Advertising Readiness Update

Manual/imported advertising metrics are the approved MVP data source. The synthetic import scenario in `docs/advertising-metrics.md` is the required pilot-safe validation path for ROAS/CPA/CPL reporting. Real Meta Ads API integration remains future work and must not be represented as active sync.

Current attribution readiness: lead source and order ad cost support manual attribution signals, while campaign attribution remains optional and documented as future enhancement. Dashboard, Analytics, and `/advertising` should use the same daily ad metrics and selected period boundaries.

## Sprint 4.2 Advertising Pilot Readiness

Sellora now has a synthetic advertising import template, a bilingual import guide, a staging QA guide, and a pilot advertising guide. Manual advertising import remains the MVP path, while Meta Ads API automation remains future work. `/advertising` and `/settings/import` now point users toward the template/download path and explain how to continue after dry-run/import.

## Sprint 4.2.1 Advertising CSV Template Validation

- The GitHub binary-file blocker is considered resolved when tracked template files are CSV-only and no UI/docs link points to `advertising-import-template.xlsx`.
- CI validation for Sprint 4.2.1 covers CSV template headers, synthetic rows, Import Center CSV upload/preview tests, full backend pytest, FastAPI app import, frontend typecheck/build, and advertising/import regression scripts.
- `next lint` remains a tooling follow-up until the project migrates from deprecated interactive `next lint` setup to an explicit ESLint CLI configuration.
- Manual browser staging QA with the CSV template remains required before declaring real staging approval; all QA data must stay synthetic.

## Sprint 4.2.2 Advertising Manual Staging Decision

- Local validation is recovered for the CSV advertising import flow, but deployed browser staging QA was not executable without staging URL, credentials, and a controlled QA workspace.
- Advertising import remains **not pilot-ready yet** until `/settings/import`, `/advertising`, Dashboard, and Analytics are verified on deployed staging with the synthetic CSV template.
- Do not mark Sprint 4.2.2 as manually approved, and do not use real ad account exports, tokens, account IDs, customer data, screenshots with secrets, or private order data for the remaining QA.

## Sprint 4.2.3 Advertising Staging Access Decision

- Required staging inputs were still unavailable: staging frontend URL, staging backend URL, secure credentials, controlled QA workspace, and role/permission confirmation.
- Advertising CSV import cannot be marked pilot-ready from local validation alone; deployed `/settings/import`, `/advertising`, Dashboard, and Analytics checks are still required.
- Final Sprint 4.2.3 decision: **Advertising import staging QA blocked** until staging access is provided and the synthetic CSV import flow is executed end-to-end.

## Sprint 4.3 Advertising Insights Readiness

- `/advertising` now includes frontend-computed campaign comparison, decision statuses, Top Campaigns, and Campaigns Needing Attention based on existing manual/imported campaign performance metrics.
- Decision support is explanatory and deterministic; it does not use AI generation, Meta Ads API data, or new backend enum values.
- Advertising import remains blocked for pilot readiness until deployed staging access, credentials, controlled workspace, and synthetic CSV import QA are completed.

## Sprint 4.3.1 Advertising Insights Validation Status

- NO_DATA campaign visibility is expected in `/advertising` comparison by merging campaign records with performance rows on the frontend.
- Decision priority is documented as `NO_DATA → PROBLEM → GOOD → WATCH`; spend with leads and zero orders remains PROBLEM with a Direct/offer review message.
- Frontend typecheck/build, browser staging, mobile, and dark/light validation must be recorded for Sprint 4.3.1 before fully approving Sprint 4.3.
- Advertising import remains blocked for pilot readiness until deployed manual import staging QA passes with synthetic data.

## Sprint 4.3.2 Advertising Insights Build and Browser QA Recovery

- Dependency recovery is still blocked in this environment: `npm ci` cannot run because no frontend lockfile is committed, `npm install` is denied by the registry/proxy for `@tanstack/react-query`, and `pip install -r backend/requirements.txt` is denied by the Python package proxy for FastAPI.
- Frontend typecheck and production build remain externally blocked because dependencies such as Next.js, React, and TanStack Query cannot be restored here; rerun both checks in an approved dependency-cache or registry environment before final Sprint 4.3 approval.
- Backend `compileall` passes for `backend/app` and `backend/tests`, but full `pytest` and FastAPI app import remain blocked until backend dependencies are available.
- Browser, mobile-width, and dark/light theme QA for `/advertising` could not be completed locally without restored frontend dependencies or a provided staging URL; the Sprint 4.3 decision therefore remains **conditionally approved** rather than fully approved.
- Full repository regression scripts for the advertising insights, import, analytics, responsive, Nova Poshta, order, localization, and pilot-readiness markers pass without code changes.
- Advertising import remains not pilot-ready until deployed manual import staging QA passes with synthetic CSV data.

## Sprint 4.3.3 Frontend Lockfile and CI Recovery

- Dependency strategy audit result: the frontend currently uses npm via `frontend/package.json`; no `package-lock.json`, `npm-shrinkwrap.json`, `yarn.lock`, or `pnpm-lock.yaml` is committed, so npm is the intended package manager but reproducible `npm ci` is not available yet.
- Lockfile creation was attempted with `npm install --package-lock-only`, but the current registry/proxy denied `@tanstack/react-query` with `403 Forbidden`; no lockfile was generated or faked.
- Recommended CI strategy remains npm with a committed `frontend/package-lock.json`, generated in an approved npm registry/cache environment, followed by `npm --prefix frontend ci`, `npm --prefix frontend run typecheck`, and `npm --prefix frontend run build`.
- Frontend typecheck/build remain blocked in this environment because dependencies cannot be restored; backend `compileall` still passes, while backend `pytest` and FastAPI app import remain blocked by missing FastAPI.
- Advertising insights regression scripts and the full relevant frontend marker suite pass; browser/mobile/theme QA remains blocked until dependencies or staging access are available.
- Final Sprint 4.3 recommendation remains **blocked** for full approval until the frontend lockfile is committed and build/browser validation can run reproducibly.

## Sprint 4.5 — Advertising reporting consolidation

Sprint 4.5 improves `/advertising` as an owner-facing MVP report. The page now clarifies the active data source, shows KPI cards, campaign decision support, manual attribution behavior, campaign/daily metric tables, trend details, import help, and a pilot readiness gate without adding Meta Ads API automation or backend enum changes.

Current advertising readiness remains conditional:

- manual metric entry, CSV template import, ROAS/CPA/CPL, deterministic campaign guidance, and manual order-to-campaign attribution are available MVP capabilities;
- PostgreSQL runtime migration validation for Sprint 4.4 attribution is still pending;
- staging/browser/mobile QA for lead/order attribution and `/advertising` is still pending;
- advertising import is not pilot-ready until manual staging import QA passes with synthetic data;
- Sprint 4.4 must not be marked fully approved until runtime and browser/staging QA are completed.

## Sprint 4.5.1 — Pilot readiness check result

Sprint 4.5.1 local validation passed, but staging/runtime validation did not proceed because required inputs were missing. Advertising remains blocked for pilot readiness until a safe staging/runtime environment is provided and the PostgreSQL migration, CSV import, browser attribution, workspace isolation, mobile, and theme QA checklists pass with synthetic data only.

Do not mark advertising import pilot-ready and do not mark Sprint 4.4 fully approved until those runtime checks are completed.

## Sprint 4.6 — Meta Ads API readiness status

Sprint 4.6 documents future Meta Ads OAuth, read-only sync, workspace/RBAC, privacy, idempotency, UI state, and future schema contracts without implementing live Meta integration.

Current status remains conditional:

- Meta Ads API is planned / architecture-ready / not active;
- manual entry and CSV import remain the MVP advertising source;
- advertising import is not pilot-ready until staging import QA passes;
- Sprint 4.4 attribution is not fully approved until PostgreSQL runtime and browser/mobile QA pass;
- no real tokens, API keys, ad account data, business IDs, customer data, or workspace IDs should appear in docs, tests, screenshots, logs, or PR text.

## Sprint 4.7 — Meta Ads fake-client simulation readiness

Sprint 4.7 adds a backend fake-client boundary, DTO contracts, mapper, and dry-run sync simulation for future Meta Ads work. This is **fake-client / simulation-ready / not active** and does not connect to Meta.

Current status remains conditional:

- manual entry and CSV import remain the MVP advertising source;
- no live Meta OAuth, live API calls, token storage, production sync jobs, database migrations, automatic attribution, or Conversions API are active;
- orders, revenue, and profit remain Sellora-side business data;
- advertising import is not pilot-ready until staging import QA passes;
- Sprint 4.4 attribution is not fully approved until PostgreSQL runtime and browser/mobile QA pass.

## Sprint 4.8 — Meta Ads sync preview readiness

Sprint 4.8 adds read-only DB comparison and sync preview on top of the fake Meta client. This is **fake-client + read-only DB comparison + sync preview ready / not active** and does not connect to Meta or write sync results to the database.

Current status remains conditional:

- manual entry and CSV import remain the MVP advertising source;
- preview uses current `workspace_id + normalized campaign name + platform` fallback matching until future external ID schema support exists;
- manual/CSV rows are protected and overlapping fake Meta rows are flagged as `POTENTIAL_CONFLICT`;
- no live Meta OAuth, live API calls, token storage, database migrations, sync-run persistence, production sync jobs, automatic attribution, or Conversions API are active;
- orders, revenue, and profit remain Sellora-side business data;
- advertising import is not pilot-ready until staging import QA passes;
- Sprint 4.4 attribution is not fully approved until PostgreSQL runtime and browser/mobile QA pass.

## Sprint 4.9 — Meta Ads external identity contract readiness

Sprint 4.9 documents future external identity, ad metric source separation, sync-run persistence, Meta connection storage, migration phases, conflict resolution, and preview-to-apply-sync rules. This is **schema design and sync persistence contract ready / not active**.

Current status remains conditional:

- manual entry and CSV import remain the MVP advertising source;
- no live Meta OAuth, live API calls, token storage, database migrations, DB writes for Meta sync, sync-run persistence implementation, production sync jobs, automatic attribution, click tracking, or Conversions API are active;
- future exact identity requires workspace-scoped `external_source`, `external_account_id`, and `external_campaign_id` support;
- future existing rows must be backfilled as `manual` or `csv_import` before Meta-owned rows can be safely separated;
- manual/CSV rows are protected, and Meta-owned rows can update only Meta-owned rows with the same external identity;
- orders, revenue, and profit remain Sellora-side business data;
- advertising import is not pilot-ready until staging import QA passes;
- Sprint 4.4 attribution is not fully approved until PostgreSQL runtime and browser/mobile QA pass.

## Sprint 4.10 — External identity migration draft readiness

Sprint 4.10 creates a nullable-first external identity/source-separation migration draft and matching model/read-only preview compatibility. Meta Ads API is **external identity schema draft prepared / runtime-gated / not active**.

Current status remains conditional:

- manual entry and CSV import remain the MVP advertising source;
- no live Meta OAuth, live API calls, token storage, `meta_ad_connections`, production sync jobs, apply-sync, Meta sync DB writes, automatic attribution, click tracking, or Conversions API are active;
- the migration draft is additive and nullable-first, but PostgreSQL runtime upgrade/downgrade/upgrade is still required on a safe non-production database;
- no destructive or guessed backfill is performed;
- orders, revenue, and profit remain Sellora-side business data;
- advertising import is not pilot-ready until staging import QA passes;
- Sprint 4.4 attribution is not fully approved until PostgreSQL runtime and browser/mobile QA pass.

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
