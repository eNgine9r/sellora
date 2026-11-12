# SA.1 → SA.2 — handoff

SA.1 adds an isolated read-only backend for the Platform Admin Center. SA.0 was merged in [PR #412](https://github.com/eNgine9r/sellora/pull/412). Use the contracts below for SA.2 after the backend PR is merged.

| GET path under `/api/v1/platform-admin` | Capability | Response |
| --- | --- | --- |
| `/me` | `platform.access` | `operator_id`, `role`, `capabilities` |
| `/summary` | `workspaces.read` | `as_of`, `total_workspaces`, `enabled_workspaces`, `demo_workspaces`, `workspaces_with_current_term` |
| `/workspaces` | `workspaces.read` | `items`, `next_cursor`, `as_of` |
| `/workspaces/{workspace_id}` | `workspaces.read` | Registry metadata, subscription, currency, timezone, `active_member_count` |
| `/workspaces/{workspace_id}/subscription` | `subscriptions.read` | Existing subscription status projection for the specified workspace |

Use `q`, `active`, `demo`, `limit` and `cursor` for server-side filtering and pagination. Omit the filter to include all values. A cursor belongs to the filter values that generated it. Reset pagination when filters change. The API orders rows by descending creation time and workspace ID.

The dashboard summary counts workspaces from the registry at `as_of`. Enabled means the workspace is enabled in settings. Current term means a stored `ACTIVE` or `TRIALING` term covers `as_of` under the half-open UTC interval. Demo and term counts can overlap the enabled count. Member count includes active, non-deleted memberships belonging to active user accounts. [Response schemas](../../../backend/app/schemas/platform_admin.py)

Authenticate with the direct password flow of the existing cookie-session API. Platform reads use the bearer access token, omit `X-Workspace-ID` and bypass shared cache. HTTP `401` requires a direct sign-in, `403` indicates missing permission, and `404` at `/me` indicates the feature is unavailable. The auditor can discover their identity. Directory and summary require admin or support capability.

Migration `202611120056` adds the password-origin marker, grants, audit and a registry pagination index. The backend defaults to `SELLORA_PLATFORM_ADMIN_ENABLED=false`. A future rollout needs migration-first deployment, cookie-session configuration, a verified app-role RLS path, and an approved operator grant. Provision grants from a trusted operator terminal with `PYTHONPATH=. python scripts/manage_platform_grants.py --help` from `backend`. The command prompts for the operator password and records an approval reference.

Targeted verification used a disposable local PostgreSQL 16 database and exercised direct/legacy login and refresh, revoked sessions/grants, denial across tenant roles, pagination, projections, aggregation, and audit. The GitHub PostgreSQL job repeats the canary in a separate database. No runtime deployment or production migration was part of SA.1.
