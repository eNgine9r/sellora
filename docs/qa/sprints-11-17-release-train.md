# Sprints 11–17 release train

This ledger prevents documentation-only approval. A sprint is `APPROVED` only when its automated gates and required external evidence are both green.

| Sprint | Engineering closure | Runtime/external gate | Current decision |
| --- | --- | --- | --- |
| 11 Security & Runtime | RBAC/tenant tests, frontend timeout, refresh mutex, localized errors, exact-commit workflows | Render/Vercel exact `main`, packaged Alembic head, browser matrix | Runtime gate required |
| 12 Fulfillment & Nova Poshta | Prepare/execute/reconcile, durable provider-confirmed TTN cancellation, idempotency and mobile wizard coverage | One controlled real TTN create/cancel or shipped parcel evidence | Engineering closure in progress; real provider gate required |
| 13 Inventory | Row locks, reservation lifecycle, archive guards, database invariant, audit trail | PostgreSQL concurrency suite on packaged head | Engineering-ready |
| 14 Finance | Canonical `ProfitCalculationService` shared by Orders/Finance/Analytics | Cross-surface staging equality for one period/workspace | Engineering-ready |
| 15 Controlled Pilot | Onboarding, support, incident, rollback, backup and reporting runbooks | 3–5 consented real pilot workspaces and restore drill | Pilot remains gated |
| 16 Advertising | Read-only OAuth/client/preview protection foundation | Approved Meta permissions and bounded daily live read-only sync | Meta approval gate required |
| 17 Mobile Discovery | Expo decision, FastAPI compatibility PoC, estimate and store plan | Expo Go device smoke test | Discovery deliverable ready |

## Release rules

- No Nova Poshta or Meta write is enabled by documentation or merge alone.
- Duplicate provider operations are measured by durable idempotency keys, never inferred from UI clicks.
- No pilot workspace is created for a real store without the store owner's consent and onboarding data.
- Public launch remains gated after Sprint 15.
- Runtime evidence must include commit SHA, Alembic revision, timestamp, and only sanitized aggregate results.
