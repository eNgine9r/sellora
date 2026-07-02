# Sellora

Sellora is a SaaS CRM foundation built as a Python/FastAPI + Next.js modular monolith. Sprint 1.1 bootstraps repository structure, infrastructure, authentication, RBAC, workspace isolation, Alembic migrations, and tests only.

> Business modules such as Leads, Orders, Customers, Products, Inventory, Advertising, Finance, and Shipments are intentionally not implemented yet.

## Project tree

```text
sellora/
├── backend/
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/202606020001_initial_foundation.py
│   ├── app/
│   │   ├── api/v1/
│   │   ├── auth/
│   │   ├── core/
│   │   ├── database/
│   │   ├── dependencies/
│   │   ├── middleware/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── utils/
│   ├── tests/
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── scripts_seed.py
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── providers/
│   │   ├── services/
│   │   └── types/
│   ├── Dockerfile
│   ├── components.json
│   ├── package.json
│   └── tailwind.config.ts
├── docs/
│   ├── architecture.md
│   ├── database_mixins.md
│   ├── future_model_examples.py
│   ├── sprint_1_2a_lead_customer_workflow.md
│   ├── sprint_1_3_products_inventory.md
│   ├── sprint_1_4_orders_profit_engine.md
│   └── sprint_1_5_crm_completion.md
├── docker-compose.yml
├── .env.example
└── README.md
```

## Architecture

- **Clean Architecture:** API routers depend on services, services depend on repositories/models, and infrastructure details stay in database/auth packages.
- **Modular Monolith:** the app starts as one deployable backend, with package boundaries ready for future feature modules.
- **Multi-Tenant SaaS:** workspaces are first-class; users join workspaces through roles; future tenant-owned entities must inherit `WorkspaceScopedMixin` and `SoftDeleteMixin`.
- **RBAC:** reusable guards support `OWNER`, `MANAGER`, and `ANALYST` authorization.
- **Auditability:** an `audit_logs` table captures lead source, lead, and customer workflow actions.
- **Lead → Customer Workflow:** Sprint 1.2A adds Lead Sources, Leads, Customers, lead assignment, lead loss, and lead conversion APIs.
- **Products & Inventory:** Sprint 1.3 adds Products, Product Variants, Product Images, Inventory, and Inventory Transactions.
- **Orders & Profit Engine:** Sprint 1.4 adds Orders, Order Items, Status History, inventory transitions, and profit calculations without standalone shipments/payments modules.
- **CRM Completion:** Sprint 1.5 adds customer tags, notes, addresses, and polymorphic attachments.

## Backend stack

- Python 3.12
- FastAPI with OpenAPI docs at `/docs`
- SQLAlchemy 2.0
- Alembic
- PostgreSQL 16
- Pydantic v2
- JWT access and refresh tokens
- Argon2 password hashing
- Pytest

## Frontend stack

- Next.js 15
- TypeScript
- TailwindCSS
- shadcn/ui-compatible Tailwind conventions
- TanStack Query

## Environment setup

Copy the example environment file before starting services:

```bash
cp .env.example .env
```

Update secrets in `.env` for any non-local environment.

For staging and production, configure database connectivity, application signing secrets, token lifetimes, and local Postgres settings through the deployment platform or a private `.env` file. Do not paste real values into docs, screenshots, logs, or pull requests.

## Startup

Start the full stack with:

```bash
docker compose up
```

Services:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Swagger/OpenAPI docs: http://localhost:8000/docs
- pgAdmin: http://localhost:5050
- PostgreSQL: localhost:5432

The backend container runs Alembic migrations and seeds default roles plus the initial admin user at startup.

Default local admin credentials from `.env.example`:

- Email: `admin@sellora.local`
- Password: `ChangeMe123!`

## Authentication endpoints

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`

## CRM endpoints

- `GET|POST /api/v1/lead-sources`
- `PUT|DELETE /api/v1/lead-sources/{id}`
- `GET|POST /api/v1/leads`
- `PUT|DELETE /api/v1/leads/{id}`
- `POST /api/v1/leads/{id}/assign`
- `POST /api/v1/leads/{id}/convert`
- `POST /api/v1/leads/{id}/mark-lost`
- `GET|POST /api/v1/customers`
- `GET|PUT|DELETE /api/v1/customers/{id}`
- `GET|POST /api/v1/products`
- `GET|PUT|DELETE /api/v1/products/{id}`
- `POST /api/v1/products/{id}/images`
- `GET|POST /api/v1/products/variants`
- `PUT|DELETE /api/v1/products/variants/{id}`
- `GET|PUT /api/v1/inventory/{id}`
- `GET /api/v1/inventory`
- `POST /api/v1/inventory/{id}/transactions`
- `GET /api/v1/inventory/transactions`
- `GET|POST /api/v1/orders`
- `GET|PUT /api/v1/orders/{id}`
- `POST /api/v1/orders/{id}/status`
- `GET /api/v1/orders/dashboard`
- `GET|POST /api/v1/tags`
- `PUT|DELETE /api/v1/tags/{id}`
- `GET|POST /api/v1/customers/{id}/notes`
- `GET|POST /api/v1/customers/{id}/addresses`
- `PUT|DELETE /api/v1/customers/{id}/addresses/{address_id}`
- `GET|POST|DELETE /api/v1/attachments`
- `GET /api/v1/analytics/sales-summary`
- `GET /api/v1/analytics/profit-summary`
- `GET /api/v1/analytics/sales-trend`
- `GET /api/v1/analytics/top-products`
- `GET /api/v1/analytics/customers-summary`
- `GET /api/v1/analytics/inventory-summary`
- `GET /api/v1/analytics/dashboard`
- `POST /api/v1/import/upload`
- `GET /api/v1/import/{job_id}/sheets`
- `POST /api/v1/import/{job_id}/preview`
- `POST /api/v1/import/{job_id}/suggest-mapping`
- `POST /api/v1/import/{job_id}/dry-run`
- `POST /api/v1/import/{job_id}/validate`
- `POST /api/v1/import/{job_id}/execute`
- `GET /api/v1/import/{job_id}/logs`
- `GET /api/v1/import/presets/your-jewelry`

The staging frontend centralizes authenticated API requests and automatically attaches the active session and workspace headers after login; do not paste or expose tokens in the UI.

## Local backend commands

From `backend/`:

```bash
pip install -r requirements.txt
alembic upgrade head
python scripts_seed.py
uvicorn app.main:app --reload
pytest
```

## Next recommended sprint

Sprint 1.9 should build on the manual advertising engine with operational readiness while still avoiding external API coupling:

1. shipment provider integration discovery;
2. membership management;
3. audit log viewer;
4. role-specific route examples;
5. frontend authentication shell;
6. Meta Ads API planning without live integration.

Do not add Nova Poshta, Instagram Graph, live Meta Ads, or AI Insights until the manual workflows and audit surfaces are stable.

## Sprint 1.8 – Advertising & ROAS Engine

Sellora now includes manual advertising campaign and daily metric tracking under `/api/v1/advertising`. The module calculates CPA, CPL, CPC, CPM, CTR, ROAS, and ROI from manually entered metrics. OWNER can create/update/delete campaigns and metrics; ANALYST can read full analytics; MANAGER can read basic performance while profit-sensitive fields are omitted.

Frontend route `/advertising` provides a campaign list, daily metrics table, KPI cards, performance table, and trend chart. The Import Center also supports `ad_campaigns` and `ad_metrics` mappings for dry-run and create-only imports without storing private spreadsheet data in the repository.

## Sprint 1.8.1 – Staging UX & Auth Stabilization

The frontend now includes a `/login` page, centralized auth storage, automatic `/auth/me` loading, first-workspace auto-selection, protected app navigation, workspace switching, and safe logout. API requests use `NEXT_PUBLIC_API_BASE_URL` and automatically attach the active session and selected workspace headers through the central API client.

No deployment architecture was changed: Vercel frontend, Render backend, and Supabase PostgreSQL remain the staging target. No Shipments, Nova Poshta API, Meta Ads API, or AI Insights were added.


## Sprint 1.9 Shipments Engine

Sellora now includes manual shipment tracking for orders, including TTN/tracking number, carrier, delivery status actions, recipient details, logistics dashboard counters, and Import Center shipment mapping support. The implementation is manual-only and does not connect to Nova Poshta or any external carrier API.

The frontend also includes mobile-friendly app navigation and Sellora branding metadata/assets for the login page, authenticated shell, favicon, and app icon. The staging deployment architecture remains Vercel frontend, Render backend, and Supabase PostgreSQL.


## Sprint 1.9.1 Staging QA & MVP Polish

The frontend now opens with a public Sellora landing page at `/`, uses `/dashboard` as the primary authenticated dashboard, and includes polished SaaS navigation, dashboard cards, charts, responsive private routes, and Sellora PNG brand assets under `frontend/public/brand/`. Backend contracts and deployment architecture are unchanged.

## Frontend dependency strategy

The frontend package manager strategy is npm. CI should use a committed `frontend/package-lock.json` as the authoritative lockfile and install dependencies with `npm --prefix frontend ci` before running `npm --prefix frontend run typecheck` and `npm --prefix frontend run build`.

Sprint 4.4.1 recovered the npm lockfile using `npm install --package-lock-only` with registry access. Keep `frontend/package-lock.json` committed, use `npm --prefix frontend ci` for reproducible installs, do not hand-write lockfiles, do not commit private `.npmrc` credentials, and do not introduce `yarn.lock` or `pnpm-lock.yaml` unless the package manager strategy is explicitly changed.

### Sprint 4.6 — Meta Ads API readiness

Sellora documents a future Meta Ads API path for OWNER-only OAuth, encrypted token storage, workspace-scoped read-only campaign metrics sync, idempotent daily metric upserts, and manual/CSV fallback. This is architecture-ready only: live Meta OAuth, live API calls, token storage implementation, automatic sync, automatic attribution, and Conversions API are not active. Manual entry and CSV import remain the current MVP advertising data source, and advertising import remains not pilot-ready until staging QA passes.

### Sprint 4.7 — Meta Ads fake-client simulation

Sellora now includes a backend-only fake Meta Ads boundary for future sync work: typed DTOs, a client protocol, deterministic fake client, mapper, and dry-run simulation service. Meta Ads API remains fake-client / simulation-ready / not active: no live OAuth, live API calls, token storage, production sync jobs, database migrations, automatic attribution, or Conversions API are active. Manual entry and CSV import remain the current MVP advertising data source, and advertising import remains not pilot-ready until staging QA passes.

### Sprint 4.8 — Meta Ads sync preview

Sellora now includes a backend-only read-only sync preview for the fake Meta Ads boundary. It compares fake Meta candidates against existing advertising snapshots and reports `WOULD_CREATE`, `WOULD_UPDATE`, `WOULD_SKIP`, `POTENTIAL_CONFLICT`, and external-ID support notes with `dry_run = true` and `db_writes = false`. Meta Ads API remains not active: no live OAuth, live API calls, token storage, database migrations, sync-run persistence, production sync jobs, automatic attribution, or Conversions API are active. Manual entry and CSV import remain the current MVP advertising data source, and advertising import remains not pilot-ready until staging QA passes.

### Sprint 4.9 — Meta Ads external identity contract

Sellora now documents the future Meta Ads external identity and sync persistence contract: workspace-scoped `external_source`, `external_account_id`, `external_campaign_id`, source separation (`manual`, `csv_import`, `meta_sync`), `meta_sync_runs`, and `meta_ad_connections` are designed for a future migration but are not applied. Meta Ads API remains schema design and sync persistence contract ready / not active: no live OAuth, live Meta API calls, token storage, database migrations, DB writes, production sync jobs, automatic attribution, or Conversions API are active. Manual entry and CSV import remain the current MVP advertising data source, advertising import remains not pilot-ready until staging QA passes, and Sprint 4.4 PostgreSQL runtime/browser QA blockers remain open.

### Sprint 4.10 — Meta Ads external identity migration draft

Sellora now has a nullable-first Alembic migration draft and SQLAlchemy model fields for future Meta Ads external identity/source separation on `ad_campaigns` and `ad_metrics`, plus read-only preview compatibility that prefers exact external identity when safely available. Meta Ads API remains external identity schema draft prepared / runtime-gated / not active: no live OAuth, live Meta API calls, token storage, `meta_ad_connections`, production sync jobs, apply-sync, or DB writes from Meta sync are active. Manual entry and CSV import remain the current MVP advertising source, and PostgreSQL runtime migration QA must pass on a safe non-production database before full approval.

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

## Finance MVP status — Epic Sprint 5A

Sellora Finance MVP provides read-only operational profit analytics for Instagram shops: revenue, COGS, gross profit, manual/CSV ad spend, shipping cost, refunds/discount placeholders, net profit, profit margin, and average order value.

Finance uses Advertising data only as conditional manual/CSV source until Advertising runtime/staging blockers are resolved.

Meta Ads API is not active.

Sellora Finance MVP is operational profit analytics, not full accounting software. Advertising 4.x remains feature-frozen and is not pilot-ready.
