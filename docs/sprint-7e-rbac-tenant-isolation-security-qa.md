# Sprint 7E — RBAC, Tenant Isolation & Security QA

## 1. Scope

Sprint 7E audited and regression-tested Sellora's server-side authentication, workspace context, RBAC enforcement, tenant isolation, nested-resource ownership checks, analytics/finance aggregation scope, frontend workspace-switch/cache policy, and safe error/secret posture.

No product feature work, Meta feature work, database schema change, Alembic migration, production credential, or production database operation was added.

## 2. Architecture and security invariants

Security boundary remains backend-enforced:

- authenticated active user;
- `X-Workspace-ID` header for workspace-scoped routes;
- active workspace membership;
- OWNER / MANAGER / ANALYST role checks;
- repository/service lookups scoped by workspace-owned object IDs;
- soft-deleted records excluded where the repository supports soft delete.

Frontend guards are UX-only and do not replace backend authorization.

## 3. Authentication inventory

- JWT creation and decoding are handled in `app.auth.jwt`.
- Current-user resolution is handled by `get_current_user`, which rejects missing credentials, invalid access tokens, and inactive/missing users.
- Login/refresh/me/logout routes are the authenticated/global auth surface.
- Frontend API calls attach the bearer token and react to authentication failures through the existing auth/API client flow.
- No security test or documentation added raw access tokens, refresh tokens, password hashes, provider tokens, or infrastructure secrets.

## 4. Endpoint inventory

Automated endpoint inventory test result:

| Metric | Count |
| --- | ---: |
| Total FastAPI API routes in inventory | 153 |
| Workspace-scoped routes classified by Sprint 7E guard | 144 |
| OWNER-only routes explicitly checked | 6 |
| Explicit global/public whitelist | `/health`, `/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/auth/me`, `/api/v1/workspaces` |

Representative route classifications:

| Endpoint | Method | Scope | Minimum role | Mutation | Security test |
| --- | --- | --- | --- | ---: | ---: |
| `/api/v1/leads` | GET | WORKSPACE_SCOPED | ANALYST+ | No | Yes |
| `/api/v1/leads` | POST | WORKSPACE_SCOPED | MANAGER+ | Yes | Yes |
| `/api/v1/orders/{order_id}` | GET | WORKSPACE_SCOPED | ANALYST+ | No | Yes |
| `/api/v1/orders/{order_id}` | PUT/DELETE | WORKSPACE_SCOPED | MANAGER+ | Yes | Yes |
| `/api/v1/workspace-users` | GET/POST | OWNER_ONLY | OWNER | POST yes | Yes |
| `/api/v1/workspace-users/{user_id}/role` | PUT | OWNER_ONLY | OWNER | Yes | Yes |
| `/api/v1/workspaces/current` | GET/PUT | WORKSPACE_SCOPED / OWNER mutation | OWNER for update | PUT yes | Yes |
| `/api/v1/advertising/campaigns` | POST | OWNER_ONLY | OWNER | Yes | Yes |
| `/api/v1/finance/adjustments` | POST | WORKSPACE_SCOPED | MANAGER+ | Yes | Yes |
| `/api/v1/analytics/dashboard-summary` | GET | WORKSPACE_SCOPED | ANALYST+ | No | Yes |

## 5. Actual role matrix

| Module / Action | OWNER | MANAGER | ANALYST |
| --- | --- | --- | --- |
| Read leads/customers/orders/products/inventory/shipments | Allowed | Allowed | Allowed |
| Create/update/archive leads | Allowed | Allowed | Denied |
| Create/update/archive customers | Allowed | Allowed | Denied |
| Create/update/archive orders | Allowed | Allowed | Denied |
| Inventory mutation | Allowed | Allowed | Denied |
| Shipment creation/update/status mutation | Allowed | Allowed | Denied |
| Finance summary/report reads | Allowed | Allowed where `ANALYST+` endpoints allow | Allowed |
| Finance adjustment mutation | Allowed | Allowed | Denied |
| Advertising campaign/metric mutation | Allowed | Denied | Denied |
| Workspace settings update | Allowed | Denied | Denied |
| Team member list/add/change-role/deactivate | Allowed | Denied | Denied |
| Profit-sensitive analytics endpoints with `OWNER, ANALYST` policy | Allowed | Denied where route is role-restricted | Allowed |

## 6. Synthetic test fixture

Automated tests use synthetic UUIDs and in-memory fake repositories/services only. Fixtures represent:

- Workspace A and Workspace B;
- OWNER, MANAGER, ANALYST memberships;
- inactive membership and inactive workspace scenarios;
- synthetic leads, customers, products, variants, inventory, orders, and finance adjustments.

No real customer, order, phone, workspace, email, token, or production identifier is used.

## 7. Tenant list isolation results

`test_lead_list_detail_update_archive_are_workspace_scoped` proves a Workspace A list returns only Workspace A leads and does not include Workspace B leads. The same test proves Workspace A detail lookup for a Workspace B lead returns no object.

## 8. Object IDOR results

Object-level IDOR coverage proves:

- Workspace A cannot detail-read Workspace B lead data through the Lead service.
- Workspace A cannot update Workspace B lead data.
- Workspace A cannot archive/delete Workspace B lead data.
- Cross-workspace variant IDs in order creation are rejected before order or inventory mutation.

## 9. Update/archive IDOR results

Update/archive IDOR coverage confirms Workspace B synthetic lead remains unchanged and unarchived after Workspace A attempts to update/delete it. No audit/business side effect is created in the fake audit sink for the denied operation.

## 10. Nested resource isolation results

Nested ownership coverage includes:

- Lead assignment now rejects inactive workspace memberships.
- Order item creation rejects a known variant ID when that variant belongs to another workspace.
- Finance adjustment creation rejects an order reference when the order does not exist in the active workspace.

## 11. Analytics isolation results

Finance summary coverage uses a fake repository that asserts every aggregation call receives the active workspace ID. Finance summary, order totals, shipment totals, manual advertising metrics, and adjustment reads are therefore verified as workspace-scoped at the service/repository boundary.

Endpoint inventory also classifies analytics, finance, advertising, dashboard/reporting, and import/report routes as workspace-scoped routes unless explicitly whitelisted.

## 12. OWNER results

OWNER-only guard tests verify that OWNER-only endpoints are inventoried and that non-owner roles are rejected by backend dependency guards. Existing workspace service logic retains owner checks for workspace settings and team management.

## 13. MANAGER results

MANAGER is allowed through `require_min_role(MANAGER)` for operational mutations. MANAGER is denied by OWNER-only guards for workspace/team/advertising admin operations.

## 14. ANALYST results

ANALYST remains read-only for operational modules. Automated guard coverage proves an ANALYST is denied by the MANAGER mutation guard.

## 15. Inactive/no-membership results

Automated tests prove:

- inactive membership returns no role;
- inactive workspace returns no role;
- valid user without workspace membership receives `403 Workspace access denied`;
- inactive assignee membership can no longer be used to assign a lead.

## 16. Workspace switch and cache results

Frontend audit result:

- `X-Workspace-ID` is still sent by the API client for workspace-scoped calls.
- Workspace switch state is centralized in the auth store.
- Workspace-scoped pages use existing API calls that depend on active workspace state and therefore refetch when workspace changes.
- Follow-up: add browser-level race-condition QA for delayed Workspace A responses after switching to Workspace B; no concrete stale-data leak was found in static audit.

## 17. Frontend route/action guard results

Frontend mobile/bottom navigation and profile/workspace menus remain UX guards only. Team and workspace settings are available through dedicated pages, but backend OWNER checks remain authoritative for workspace/team mutations. Direct API attempts by MANAGER/ANALYST are denied by backend guards or workspace service owner checks.

## 18. Audit logging review

Audit logging exists for key Lead, Order, Shipment, workspace settings, and selected workspace/team mutations where current services write audit records. Missing audit events that require new tables/columns were not implemented because Sprint 7E forbids migrations.

Follow-up: standardize audit coverage for every team add/change/deactivate path and every finance adjustment mutation in a future security hardening sprint if current audit requirements expand.

## 19. Error and secret safety

Safety scans were run for common secret/token/password patterns, real customer/order patterns, and hardcoded workspace IDs. Expected development/documentation references to environment-variable names and synthetic tests were reviewed; no committed real credential, token, real customer data, or private workspace ID was introduced.

## 20. Bugs found

| Severity | Affected area | Root cause | Fix | Regression test |
| --- | --- | --- | --- | --- |
| Major | Lead assignment nested tenant integrity | `_validate_assigned_user` checked only that a user had any membership with the workspace ID and did not require the membership/workspace to be active. | Require matching workspace ID, active membership, and active workspace before allowing assignment. | `test_lead_assignment_rejects_inactive_workspace_membership` |

## 21. Fixes implemented

- Hardened Lead assignee validation so inactive workspace memberships and inactive workspaces cannot be used for Lead assignment or creation.
- Added security test coverage for workspace role resolution, no-membership denial, OWNER-only guard denial, ANALYST mutation denial, lead list/detail/update/archive IDOR, nested order item isolation, finance order-reference isolation, and finance aggregation scoping.

## 22. Tests added

Added backend security tests under `backend/tests/security/`:

- `test_auth_workspace_rbac.py`
- `test_endpoint_inventory.py`
- `test_tenant_object_isolation.py`
- `test_analytics_finance_scope.py`

Added frontend/docs regression guard:

- `frontend/scripts/rbac-tenant-security-regression.mjs`

## 23. Remaining gaps

- Manual browser/mobile role QA remains recommended for direct routes, mobile navigation, and workspace switch race-condition behavior.
- Sprint 7F runtime PostgreSQL migration closure remains blocked separately and is not resolved by Sprint 7E.
- Audit logging is reviewed but not fully standardized for every possible critical event; expanding audit schema/coverage may require a future approved migration or service hardening task.
- The new security suite covers representative high-risk modules and shared guards; future sprints should continue expanding endpoint-level API tests as more routes become production-critical.

## 24. Final recommendation

**Sprint 7E — CONDITIONALLY APPROVED ⚠️**

Automated negative tests now prove the core RBAC and tenant-isolation invariants for shared guards and representative high-risk business flows, and a confirmed nested-membership bug was fixed. Conditional status is used because manual browser/mobile race-condition QA and broader audit-log standardization remain follow-ups.

## 25. Sprint 7E.1 closure update

Sprint 7E.1 adds explicit request-body workspace-injection negative tests, frontend clean `npm ci` recovery using the tracked npm lockfile, React Query workspace-switch cache cancellation/invalidation, exact endpoint inventory reconciliation, and a dedicated audit logging backlog.

Updated recommendation: **Sprint 7E — APPROVED ✅**.

Sprint 7F Runtime Migration Closure remains separately **BLOCKED ⚠️** until an approved PostgreSQL runtime environment is available.
