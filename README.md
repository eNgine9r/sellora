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
│   └── future_model_examples.py
├── docker-compose.yml
├── .env.example
└── README.md
```

## Architecture

- **Clean Architecture:** API routers depend on services, services depend on repositories/models, and infrastructure details stay in database/auth packages.
- **Modular Monolith:** the app starts as one deployable backend, with package boundaries ready for future feature modules.
- **Multi-Tenant SaaS:** workspaces are first-class; users join workspaces through roles; future tenant-owned entities must inherit `WorkspaceScopedMixin` and `SoftDeleteMixin`.
- **RBAC:** reusable guards support `OWNER`, `MANAGER`, and `ANALYST` authorization.
- **Auditability:** an `audit_logs` table is ready for future entity change tracking.

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

Use `Authorization: Bearer <access_token>` for authenticated requests. Workspace-scoped routes in future sprints should also pass `X-Workspace-ID`.

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

Before Sprint 1.2 business work, future entities should follow the database mixin contract documented in `docs/database_mixins.md`. Sprint 1.2 should add workspace administration screens and APIs only:

1. workspace settings read/update;
2. user invitation flow;
3. membership management;
4. audit log write helpers;
5. role-specific route examples;
6. frontend authentication shell.

Do not add CRM business modules until the identity, tenancy, and workspace administration surfaces are complete.
