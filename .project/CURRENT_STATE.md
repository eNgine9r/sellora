# Sellora Current State

Updated: 2026-07-31
Status confidence: provisional until the reconciliation work package is completed.

## Profile

- Project type: CLOUD_SAAS
- Frontend: Next.js deployed to Vercel
- Backend: FastAPI deployed to Render
- Database: Supabase PostgreSQL
- Product language: Ukrainian-first
- Core controls: workspace isolation, backend RBAC, migrations and auditability

## Active process Sprint

Development operating standard adoption and state reconciliation.

- Work Package 232: workflow foundation — in progress.
- Work Package 233: reconcile code, documentation, roadmap and runtime — Ready after the foundation.

## Operating decision

All new work follows this path:

Product request → scoped Issue → branch → implementation → targeted checks → Pull Request → CI and runtime evidence → state update → Done.

Chat history is not the only accepted record of a decision or completed task.

## Repository facts already confirmed

- The root agent instructions contain detailed product, architecture, security, localization and domain constraints.
- The repository documents a FastAPI, SQLAlchemy, Alembic, PostgreSQL, Next.js and TypeScript architecture.
- Historical Sprint documentation exists and must be reconciled against current code and deployed runtime.

## Items still requiring verification

- latest fully completed product Sprint;
- current staging frontend and backend commit alignment;
- current staging migration head;
- relationship between open Issues, Pull Requests and roadmap;
- stale or contradictory documentation;
- current CI and browser verification status.

## Next action

Complete Work Package 233 and replace this provisional baseline with evidence-backed project state.
