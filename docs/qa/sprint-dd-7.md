# Sprint Dd.7 — Settings, Workspace, Team & Final Design QA

## Pre-implementation audit

### Routes discovered

| Route | Purpose | Existing actions | API/service surface | Notes |
| --- | --- | --- | --- | --- |
| `/settings` | Settings overview | Linked import, integrations, feedback; inline language/workspace controls existed | `useAuth`, workspace summary | Was a page-local centered shell with hard-coded light colors. |
| `/settings/workspace` | Current workspace settings | Update name, slug, currency and timezone | `fetchWorkspaceSettings`, `updateWorkspaceSettings` with `X-Workspace-ID` | OWNER-only UI; backend remains source of authorization. |
| `/settings/team` | Team access management | Add user with temporary password, role update, deactivate | `fetchWorkspaceUsers`, `addWorkspaceUser`, `updateWorkspaceUserRole`, `deactivateWorkspaceUser` | Current flow creates a user/member directly; no email invitation service was found. |
| `/settings/import` | Import Center | Upload, sheet preview, mapping suggestion, validation, dry-run, execute import, logs for current job | `import-center` service functions scoped by workspace | Preserves Your Jewelry presets and `affect_inventory` safety option. |
| `/settings/integrations` | Integration configuration | Nova Poshta save/test/disconnect; Meta Ads readiness card | `fetchNovaPoshtaSettings`, `saveNovaPoshtaSettings`, `testNovaPoshtaConnection`, `disconnectNovaPoshta` | Meta Ads remains readiness/manual-import state; no live sync claim added. |
| `/settings/feedback` | Pilot feedback management | OWNER status update; OWNER/MANAGER view | `fetchPilotFeedback`, `updatePilotFeedbackStatus` | Existing route retained as a real Settings card. |

### Workspace contract

- Workspace settings expose `id`, `name`, `slug`, `currency_code`, `timezone`, `role` and `is_active` through frontend types.
- Workspace settings update accepts `name`, `slug`, `currency_code` and `timezone` only.
- Workspace requests include active workspace context through `X-Workspace-ID` in `workspaceHeaders`.
- No workspace archive/delete/transfer endpoint was present in the frontend service layer, so the redesigned page documents that danger-zone actions are unavailable instead of adding fake controls.

### Team contract

- Workspace member records expose `user_id`, `email`, `full_name`, `role` and `is_active`.
- Supported roles remain backend enum values `OWNER`, `MANAGER`, and `ANALYST`; translations are UI-only.
- Add-user payload contains `email`, `full_name`, `role`, and `temporary_password`. The UI therefore uses “Add user”, not “Invite”.
- Deactivation is supported; reactivation, hard-delete, pending invites, last activity and seat limits were not found in the current frontend contract.
- The frontend now prevents obvious invalid actions for the final active OWNER and the current user, while backend authorization remains authoritative.

### Import and integrations

- Import Center supports upload, sheet selection, preview, mapping suggestion, validation, dry-run and execute flows; these were preserved.
- Your Jewelry presets exist for general import, product catalog, order history and advertising history.
- Nova Poshta settings support save/test/disconnect through real endpoints. Secrets remain handled by the existing integration component and are not rendered in the Settings overview.
- Meta Ads is represented through the existing readiness card and manual/CSV import language; no fake live sync or OAuth action was added.

## Implementation decisions

- Reused `WorkspacePage`, `WorkspaceHeader`, `CompactSummary`, `Card`, `Button`, `FormField`, `Input`, `Select`, `StatusBadge`, `Modal`, and `ConfirmationDialog` instead of adding a separate Settings design language.
- Settings navigation is based only on real discovered routes.
- Workspace form tracks dirty state, disables save when unchanged, preserves data after save errors, and reloads from workspace-scoped query data after workspace changes.
- Team pagination is below the list. Because the current team API returns an array rather than paginated metadata, the summary and pagination are explicitly scoped to the current API response.
- No backend, schema, RBAC or workspace-isolation behavior was changed.

## Final QA status

- Static final QA was completed through code inspection and regression scripts for Dd.1–Dd.7 shared patterns.
- Authenticated browser QA across the full viewport, role and workspace-switch matrix remains pending in this environment; final sprint status is therefore conditional, not fully approved.
