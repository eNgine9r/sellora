# Sprint Admin Roles & Users

Sprint Admin Roles & Users adds multi-workspace MVP, workspace switcher, workspace settings, and team management.

OWNER can create and manage workspace/team.

MANAGER and ANALYST cannot manage workspace/team.

User can belong to multiple workspaces.

Deactivation is workspace-level through workspace_user.is_active=false.

Email invitations, password reset, billing, super admin, and audit log UI remain out of scope.

## Topbar overlay UX follow-up

Workspace and user actions were moved into safer profile/mobile overlay menus to avoid header overflow and clipped dropdowns.

## Sprint 7A stabilization note

The no-workspace onboarding path now keeps authenticated users in the app and offers first-workspace creation instead of treating missing memberships as an unauthenticated session.

## Sprint 7A.1 QA closure note

Manual staging QA closure remains blocked from this validation container because the staging frontend and backend cannot be reached through the proxy. No test passwords are documented.

## Sprint 7F runtime migration status

Admin Roles & Users migration `202607050019_admin_roles_users` remains statically reviewed and locally validated, but runtime approval is blocked until `alembic upgrade head` can connect to the safe non-production PostgreSQL database and verify `workspaces.timezone` plus `workspace_users.is_active`, timestamps, soft-delete field, and indexes.

## Sprint 7E security note

Sprint 7E confirms that workspace/team management remains OWNER-only on the backend. MANAGER and ANALYST direct API attempts for team creation, role changes, membership deactivation, and workspace settings updates are denied by backend guards or workspace service owner checks. Inactive memberships are not valid workspace authorization.
