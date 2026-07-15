# Sprint 7E.1 — Security Closure & Frontend CI Recovery

## Summary

Sprint 7E.1 closes the remaining Sprint 7E security and CI gaps without adding product features, migrations, new roles, schema changes, Meta/Nova Poshta expansion, billing, or destructive data operations.

## Lockfile investigation

| Question | Finding |
| --- | --- |
| Official package manager | npm, based on `frontend/package.json` scripts and existing lockfile format. |
| Current lockfile | `frontend/package-lock.json` is present and tracked. |
| Lockfile history | The lockfile was introduced in commit `17cebc5 Recover advertising attribution validation`; earlier docs recorded that no authoritative lockfile existed. |
| Ignored by `.gitignore` | No. `.gitignore` ignores `frontend/node_modules/`, `frontend/.next/`, and `*.tsbuildinfo`, not `frontend/package-lock.json`. |
| Other lockfiles | No `npm-shrinkwrap.json`, `yarn.lock`, or `pnpm-lock.yaml` is used. |
| CI/Vercel expectation | No GitHub workflow was present; npm remains the established frontend package manager. |
| Recovery method | Use the tracked npm lockfile and validate it from a clean dependency state with `npm --prefix frontend ci`. |
| Dependency diff | No package manager switch or broad dependency upgrade was introduced in Sprint 7E.1. |

## Workspace injection result

Automated service-level tests were added in `backend/tests/security/test_workspace_injection.py`.

| Scenario | Result |
| --- | --- |
| Create payload injection | A payload containing `workspace_id` cannot override the server workspace context; the created product remains in Workspace A and no Workspace B product is created. |
| Update payload injection | A payload containing `workspace_id`/`tenant_id` cannot move an existing Workspace A product to Workspace B; Workspace B object remains unchanged. |
| Nested tenant injection | Creating a Workspace A variant referencing a Workspace B product is rejected before variant, inventory or audit side effects. |

## Workspace-switch cache safety

Implemented frontend cache hardening in `AuthProvider`:

- workspace-scoped query keys already include the active workspace ID for core modules such as Dashboard, Leads, Orders, Customers, Inventory, Shipments, Advertising, Finance, Analytics and Settings;
- `switchWorkspace` cancels active React Query requests before updating the active workspace ID and invalidates queries after the switch;
- selected workspace-bound entity state is cleared in the route pages through existing `useEffect(..., [workspaceId])` patterns;
- logout clears `authStorage` and the private React Query cache;
- stale delayed Workspace A responses remain associated with Workspace A query keys and cannot hydrate Workspace B keys.

Static regression proof is implemented in `frontend/scripts/security-closure-ci-regression.mjs`. A full browser race-condition test remains a future enhancement because this repository does not currently include a frontend component test framework and Sprint 7E.1 forbids adding a large new test stack.

## Endpoint inventory reconciliation

Primary classifications are mutually exclusive; permission flags are subsets and may overlap.

| Metric | Count |
| --- | ---: |
| Total application routes | 153 |
| Public routes | 3 |
| Authenticated global routes | 4 |
| Workspace-scoped routes | 134 |
| Feature-gated routes | 12 |
| Internal/docs routes | 0 |
| OWNER-only subset | 6 |
| Mutation routes | 84 |

Primary classification total: `3 + 4 + 134 + 12 + 0 = 153`.

OWNER-only routes are a permission subset of workspace-scoped or feature-gated routes, not an additional primary classification.

## Audit logging backlog

Audit logging is not claimed complete. Missing/partial areas are registered in `docs/security-audit-logging-backlog.md`, covering role changes, member creation/deactivation, workspace settings, inventory mutations, order status changes, finance adjustments, profit-affecting changes and critical archive actions.

## Sprint status

- Sprint 7E — APPROVED ✅
- Sprint 7E.1 — APPROVED ✅
- Sprint 7F Runtime Migration Closure — BLOCKED ⚠️ until an approved PostgreSQL runtime environment is available.
