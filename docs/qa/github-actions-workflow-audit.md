# GitHub Actions Workflow Audit

Date: 2026-07-18

Base commit: `6fa3e604cd2905ded8e10b5679bbf26e76227eab`

## Decision

Sellora now uses one canonical required CI workflow with stable product-level check names. Runtime probes that require hosted staging credentials are manual workflows and are not required for normal pull requests.

## Workflow inventory before cleanup

| File | Displayed name | Trigger | Primary responsibility | Duplication / risk | Decision |
| --- | --- | --- | --- | --- | --- |
| `.github/workflows/sprint-8f-1-fulfillment-closure.yml` | Sprint 8F.1 Fulfillment Closure Gate | PR + push to `main` | compile, focused backend, full backend, PostgreSQL, frontend | Duplicated full backend/frontend and overlapped Sprint 8F foundation/premerge gates | Merged into `ci.yml`, then removed |
| `.github/workflows/sprint-8f-foundation-gate.yml` | Sprint 8F Foundation Gate | path-filtered PR + manual | phone/CRM/Nova Poshta tests, full backend, migration gate | Duplicated full backend; Sprint-specific permanent name | Unique tests and migration script moved into `ci.yml`, then removed |
| `.github/workflows/sprint-8c-premerge.yml` | Sprint 8C/8D/8E Premerge | path-filtered PR | import/onboarding/security/operational tests and frontend build | Duplicated frontend build and backend coverage; used diagnostic `set +e` followed by separate enforcement | Unique suites moved into `ci.yml`, then removed |
| `.github/workflows/sprint-8c-storage-readiness.yml` | Sprint 8C Storage Readiness | path-filtered PR | hosted staging storage probe using secrets | External hosted mutation/readiness check was incorrectly tied to PR changes | Retained as manual-only `Sellora Storage Readiness` |
| `.github/workflows/sprint-8c-restart-prepare.yml` | Sprint 8C Restart Boundary Prepare | path-filtered PR | hosted restart-boundary preparation using secrets | Runtime workflow was incorrectly tied to PR changes | Retained as manual-only `Sellora Restart Boundary Check` |

## Workflow inventory after cleanup

| File | Displayed name | Trigger | Required | Purpose |
| --- | --- | --- | --- | --- |
| `.github/workflows/ci.yml` | Sellora CI | PR to `main`, push to `main` | Yes | Canonical static, focused, full, PostgreSQL, frontend and security gates |
| `.github/workflows/sprint-8c-storage-readiness.yml` | Sellora Storage Readiness | `workflow_dispatch` | No | Explicit hosted storage readiness validation with staging secrets |
| `.github/workflows/sprint-8c-restart-prepare.yml` | Sellora Restart Boundary Check | `workflow_dispatch` | No | Explicit restart-boundary preparation and sanitized evidence |

## Canonical required checks

- `Sellora CI / backend-static`
- `Sellora CI / backend-focused`
- `Sellora CI / backend-full`
- `Sellora CI / postgresql-integration`
- `Sellora CI / frontend-production`
- `Sellora CI / security-and-tenant-isolation`
- `Vercel`

The following checks must remain optional/manual:

- Supabase Preview
- Sellora Storage Readiness
- Sellora Restart Boundary Check
- controlled Nova Poshta provider smoke workflows
- hosted deployment verification workflows

## Coverage preserved in Sellora CI

### Backend static

- Python 3.12
- application, Alembic and script compilation
- exact single Alembic head assertion

### Backend focused

- Ukrainian phone normalization
- CRM address behavior
- Nova Poshta settings/provider-write safety
- Sprint 8F foundation migration contract
- canonical fulfillment workflow/API/finance/consolidation
- provider payload and durable TTN behavior

### Security and tenant isolation

- endpoint inventory
- tenant object isolation
- workspace injection
- runtime identity
- import provenance and formula rejection
- onboarding/demo workspace behavior
- order, inventory and shipment operational invariants

### PostgreSQL integration

- PostgreSQL 16 service
- Sprint 8F migration gate
- upgrade to current head
- downgrade to `202607180025`
- re-upgrade to head
- fulfillment concurrency and consolidation tests

### Frontend production

- deterministic `npm ci`
- TypeScript typecheck
- ESLint
- Next.js production build
- import-center static regression
- orders/inventory/shipments static regression
- Nova Poshta static regression

## Security and reliability controls

- workflow permissions are `contents: read`;
- checkout credentials are not persisted;
- PR runs use concurrency cancellation for superseded commits;
- `main` verification is not cancelled by a later run;
- all required jobs have bounded timeouts;
- PostgreSQL tests are not allowed to fall back to SQLite;
- provider writes are disabled in CI;
- secrets and workspace identifiers must not be written to artifacts;
- manual hosted workflows require an explicit confirmation value.

## Required repository rules

A `main` ruleset must require the stable checks listed above, require the branch to be up to date, require conversation resolution, block force pushes and branch deletion, and prevent normal bypass.

Repository-rules configuration is a GitHub settings operation and must be verified independently. Until evidence exists, branch protection status remains `MANUAL_ACTION_REQUIRED`.
