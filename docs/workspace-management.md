# Workspace management

Authenticated users can create workspaces, become OWNER of created workspaces, list active memberships, switch active workspace in the frontend, and send `X-Workspace-ID` for workspace-scoped API calls.

Sprint Admin Roles & Users adds multi-workspace MVP, workspace switcher, workspace settings, and team management.

## Topbar overlay UX follow-up

Workspace and user actions were moved into safer profile/mobile overlay menus to avoid header overflow and clipped dropdowns.

## Sprint 7A stabilization note

Workspace switching is constrained to active memberships already loaded for the authenticated user. First-workspace creation remains available from the onboarding/profile workspace menu.

## Sprint 7A.1 QA closure note

Workspace creation, switching, settings, team management, and data isolation require final manual staging validation from an environment with access to the staging URLs.

## Sprint 7F runtime migration status

Workspace-management runtime schema verification remains pending because the PostgreSQL host was unreachable from this container. Required checks include `workspaces.timezone`, `currency_code`, workspace-user active/timestamp fields, membership uniqueness, and workspace/user indexes.
