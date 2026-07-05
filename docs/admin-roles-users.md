# Sprint Admin Roles & Users

Sprint Admin Roles & Users adds multi-workspace MVP, workspace switcher, workspace settings, and team management.

OWNER can create and manage workspace/team.

MANAGER and ANALYST cannot manage workspace/team.

User can belong to multiple workspaces.

Deactivation is workspace-level through workspace_user.is_active=false.

Email invitations, password reset, billing, super admin, and audit log UI remain out of scope.

## Topbar overlay UX follow-up

Workspace and user actions were moved into safer profile/mobile overlay menus to avoid header overflow and clipped dropdowns.
