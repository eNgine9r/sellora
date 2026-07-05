# Sprint 7A — SaaS Admin Workspace QA & Stabilization

## 1. Scope

Sprint 7A validates and stabilizes the SaaS admin experience after Sprint Admin Roles & Users and the topbar/profile/mobile overlay fix.

Covered areas:

- login by role;
- workspace switching and creation;
- workspace settings;
- team management;
- OWNER / MANAGER / ANALYST restrictions;
- profile menu and mobile More sheet behavior;
- empty/onboarding workspace state;
- workspace data isolation guardrails;
- migration readiness for `202607050019_admin_roles_users`.

No Meta-specific logic, billing, email invitations, password reset, force password change, or organization-level super admin work is included.

## 2. Staging environment

- Frontend staging URL: `https://sellora-web-staging.vercel.app`
- Backend staging URL: `https://sellora-api-staging.onrender.com`

Staging network QA from this container is blocked by the environment proxy. `curl` to both staging hosts failed with `CONNECT tunnel failed, response 403`, so browser/runtime staging confirmation remains pending outside this sandbox.

## 3. Test accounts used by role

Accounts were referenced by role only and passwords were not documented:

- OWNER test account
- MANAGER test account
- ANALYST test account

## 4. Workspace creation QA

Local static/build validation confirms the create-workspace flow remains reachable through the workspace menu content used by the desktop profile menu and mobile More sheet.

Staging runtime confirmation is pending because the staging URLs are not reachable from this container.

## 5. Workspace switching QA

Implemented stabilization:

- `switchWorkspace` now only accepts workspaces present in the authenticated user's active memberships.
- Workspace creation stores the newly created workspace id, reloads the current user, and then lets normal membership fallback select the accessible workspace.
- This avoids persisting arbitrary workspace ids from the frontend while preserving the create-workspace flow.

Staging runtime confirmation is pending.

## 6. Workspace settings QA

Local build/typecheck/regression validation confirms `/settings/workspace` exists and contains access-denied labels for non-OWNER roles.

Staging OWNER/MANAGER/ANALYST runtime checks are pending.

## 7. Team management QA

Local build/typecheck/regression validation confirms `/settings/team`, add-user UI, duplicate membership messaging, and last OWNER protection markers exist.

Staging team management runtime checks are pending.

## 8. Role restrictions QA

Backend tests and static checks cover workspace RBAC and tenant guardrails. Staging role login and runtime mutation attempts are pending because staging is unreachable from this container.

## 9. Created user login QA

Pending staging runtime QA. Do not include temporary passwords in docs, screenshots, console output, or network logs.

## 10. Topbar/profile/mobile overlay QA

Local static/build validation confirms:

- workspace controls are no longer rendered as a standalone topbar selector;
- desktop profile menu contains workspace controls;
- mobile More sheet exists;
- portal/bottom-sheet overlay usage exists;
- create workspace and logout remain reachable.

Manual browser QA is still required for 375px, 390px, 430px, and 768px widths.

## 11. Onboarding/empty workspace state QA

Implemented stabilization:

- a user with no active workspace remains authenticated instead of being treated as unauthenticated;
- protected app routes render a safe empty-workspace onboarding state;
- the onboarding state offers first-workspace creation and uses Ukrainian MVP copy.

Staging runtime confirmation is pending.

## 12. Data isolation QA

Static and backend regression coverage continue to validate tenant and workspace guardrails. Full staging data isolation QA with synthetic records remains pending.

## 13. Runtime migration QA

Local Alembic static validation should confirm one head and the expected migration order. Runtime `alembic upgrade head` must only run against a safe non-production PostgreSQL database.

Runtime migration QA remains pending because no safe database was provided in this container.

## 14. Remaining blockers

- Staging frontend and backend are unreachable from this container due to proxy `CONNECT tunnel failed, response 403`.
- Manual browser QA is still required for role login, workspace creation/switching/settings/team flows, mobile breakpoints, and dark/light visual checks.
- Runtime PostgreSQL migration QA remains pending on a safe non-production database.

## 15. Final recommendation

Sprint 7A is conditionally approved for code stabilization and local validation, but staging runtime QA remains blocked by environment network access and must be completed before full approval.
