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

Required variables include:

- `DATABASE_URL`
- `SECRET_KEY`
- `JWT_SECRET`
- `JWT_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `IMPORT_STORAGE_PATH`
- `IMPORT_MAX_FILE_SIZE_MB`

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
