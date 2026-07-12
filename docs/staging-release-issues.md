# Staging Release Issues — Sprint 8A

| ID | Severity | Gate | Page/API | Issue | Expected | Status |
|---|---|---|---|---|---|---|
| 8A-QA-001 | Critical | G0 | `https://sellora-web-staging.vercel.app/` | Frontend staging could not be reached from this container; proxy returned `CONNECT tunnel failed, response 403`. | Frontend should serve the Sellora app over HTTPS. | Open — blocks Sprint 8A execution evidence. |
| 8A-QA-003 | Critical | G0 | `https://sellora-api-staging.onrender.com/health` | Backend health could not be reached from this container; proxy returned `CONNECT tunnel failed, response 403`. | Backend `/health` should return HTTP 200 from the staging API. | Open — blocks Sprint 8A execution evidence. |
| 8A-QA-004 | Major | G1 | Staging credentials | OWNER, MANAGER and ANALYST credentials were unavailable in `STAGING_*` environment variables. | Full release gate requires role-specific staging credentials. | Blocked — provide secure synthetic QA credentials outside the repository. |
| 8A-QA-005 | Major | G6 | Core E2E order flow | Synthetic order flow was not executed because staging access and credentials were unavailable. | A synthetic order should be creatable, openable and safely updateable before pilot release. | Blocked — rerun after G0/G1 unblock. |
| 8A-QA-006 | Major | Database/runtime | Runtime Alembic revision | Runtime migration revision was not safely available. Sprint 7F remains blocked. | Database compatibility must be independently verified before GREEN release. | Blocked — handle in Sprint 7F/runtime environment closure. |

No Critical or Major Sellora application bug was confirmed because the staging application could not be reached. The current release decision is RED due to missing evidence and blocked access, not due to a proven app-level data leak or core-flow corruption.
