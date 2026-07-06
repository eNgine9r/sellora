# Sprint 7A.1 — Manual Staging QA Closure for SaaS Admin Workspace Flow

## 1. Scope

Sprint 7A.1 is a manual staging QA closure sprint for the SaaS admin workspace flow after Admin Roles & Users, the topbar/profile mobile overlay cleanup, and Sprint 7A stabilization.

The scope is QA/readiness only:

- staging availability;
- OWNER, MANAGER, and ANALYST login behavior;
- workspace creation and switching;
- workspace settings;
- team management;
- created user login where synthetic users are created;
- no-workspace onboarding;
- data isolation;
- desktop profile menu;
- mobile More sheet;
- runtime migration status.

No Meta-specific logic, billing, email invitations, SMTP, password reset, force password change, organization-level super admin, or large feature modules are included.

## 2. Staging environment

- Frontend staging: `https://sellora-web-staging.vercel.app`
- Backend staging: `https://sellora-api-staging.onrender.com`

Environment result from this container:

- Frontend request: blocked by proxy with `CONNECT tunnel failed, response 403`.
- Backend `/health` request: blocked by proxy with `CONNECT tunnel failed, response 403`.

Because both staging URLs are unreachable from this container, manual browser QA and API runtime QA must be completed from a network environment that can reach Vercel and Render staging.

## 3. Test roles used without passwords

The intended staging roles are:

- OWNER
- MANAGER
- ANALYST

Passwords, cookies, tokens, Authorization headers, and private workspace IDs were not written to this report.

## 4. OWNER login QA

Status: **Blocked in this container**.

Reason: staging frontend/backend cannot be reached from this network. OWNER login must be tested manually from an environment with staging access.

Expected checks remain:

- OWNER can log in;
- OWNER stays authenticated;
- current workspace loads;
- profile menu shows user/workspace controls;
- no invalid `X-Workspace-ID` loop;
- reload preserves session.

## 5. MANAGER login QA

Status: **Blocked in this container**.

Expected checks remain:

- MANAGER can log in;
- MANAGER sees only accessible workspaces;
- MANAGER cannot manage workspace settings or team;
- MANAGER sees safe access-denied/read-only behavior.

## 6. ANALYST login QA

Status: **Blocked in this container**.

Expected checks remain:

- ANALYST can log in;
- ANALYST sees only accessible workspaces;
- ANALYST cannot manage workspace settings or team;
- ANALYST can access read-only areas allowed by role policy.

## 7. Workspace creation QA

Status: **Pending manual staging QA**.

Local static/build validation confirms the create-workspace form remains reachable through workspace menu/profile/mobile paths. Runtime staging validation must confirm that an OWNER can create a synthetic workspace without Swagger/API.

Recommended synthetic data:

- Name: `QA Workspace <date-time>`
- Slug: `qa-workspace-<date-time>`
- Currency: `UAH`
- Timezone: `Europe/Kyiv`

## 8. Workspace switching QA

Status: **Pending manual staging QA**.

Local code stabilization already restricts frontend switching to memberships loaded for the authenticated user. Manual staging QA must verify selected workspace persistence after reload and that workspace-scoped pages use the selected workspace.

## 9. Workspace settings QA

Status: **Pending manual staging QA**.

Expected:

- OWNER can update name, slug, currency, and timezone;
- MANAGER and ANALYST see `У вас немає доступу до керування робочим простором.`;
- backend blocks non-OWNER mutation attempts.

## 10. Team management QA

Status: **Pending manual staging QA**.

Expected:

- OWNER can open Team page and add MANAGER, ANALYST, and OWNER synthetic users;
- duplicate membership shows `Користувач уже доданий до команди.`;
- last active OWNER downgrade/deactivation is blocked;
- MANAGER/ANALYST cannot add users, change roles, or deactivate users.

## 11. Created user login QA

Status: **Pending manual staging QA**.

If synthetic users are created during manual QA, verify each new role can log in with its temporary password and cannot access unauthorized workspace/team actions. Do not document temporary passwords.

## 12. No-workspace onboarding QA

Status: **Partially stabilized locally; pending staging runtime QA**.

Implemented behavior from Sprint 7A:

- a user with no active workspace remains authenticated;
- the app shows onboarding copy instead of redirecting to login;
- the user can create a first workspace from the onboarding state.

Expected Ukrainian copy:

```text
У вас ще немає робочого простору.
Створіть перший магазин, щоб почати роботу в Sellora.
```

## 13. Data isolation QA

Status: **Pending manual staging QA**.

Manual QA must create synthetic data in Workspace A, switch to Workspace B, and confirm no lead/customer/product/order/team/settings data leaks across workspaces.

## 14. Topbar/profile desktop QA

Status: **Pending manual browser QA**.

Local static regression confirms the standalone workspace selector is not rendered directly in `AppTopbar` and workspace controls are inside the profile menu. Browser QA must verify the menu is visible, not clipped, and closes on outside click/Escape.

## 15. Mobile More sheet QA

Status: **Pending manual browser QA**.

Manual QA must verify 375px, 390px, 430px, and 768px widths for:

- no topbar overflow;
- More button visibility;
- bottom sheet visibility and internal scrolling;
- workspace switching and creation;
- settings links;
- language/theme controls;
- logout;
- dark/light readability.

## 16. Runtime migration QA

Status: **Pending safe non-production PostgreSQL database**.

Static Alembic validation should be run locally. Runtime validation must be run only on a safe non-production DB:

```bash
cd backend
alembic current
alembic heads
alembic upgrade head
alembic current
python -m pytest
python -c "from app.main import app; print('app import ok')"
```

Expected migration: `202607050019_admin_roles_users`.

## 17. Bugs found

No new application bug could be confirmed from staging because staging is unreachable from this container.

Confirmed environment blocker:

- Severity: Blocker for manual staging QA in this container.
- Area: staging access.
- Issue: both Vercel frontend and Render backend requests fail with proxy `CONNECT tunnel failed, response 403`.
- Fix/follow-up: run manual QA from an environment with staging network access.

## 18. Fixes applied

No new feature code was added in Sprint 7A.1. This pass adds the manual QA closure report and a static regression script for QA-report/readiness guardrails.

## 19. Remaining blockers

- Staging role login QA is not complete.
- Workspace creation/switching/settings/team staging QA is not complete.
- Created user login staging QA is not complete.
- Data isolation staging QA is not complete.
- Desktop/mobile browser QA is not complete.
- Runtime PostgreSQL migration QA is not complete.

## 20. Final recommendation

**Sprint 7A.1 BLOCKED ⚠️** for full approval because staging cannot be accessed from this container and role/workspace/team/mobile runtime QA cannot be completed here.

Local validation can continue to pass, but final approval requires manual staging QA from an accessible network and runtime migration QA on a safe non-production PostgreSQL database.
