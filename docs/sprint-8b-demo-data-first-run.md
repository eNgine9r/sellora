# Sprint 8B — Demo Data & First-run Experience

## Scope
Sprint 8B adds real first-run guidance, workspace-scoped onboarding status, and a separate synthetic demo workspace flow. It does not add public self-service signup, billing, live Meta/Instagram sync, Nova Poshta TTN creation, migrations, or unrestricted production launch.

## Pre-implementation inventory
- Workspace creation already lives in `WorkspaceService` and `WorkspaceRepository`; Sprint 8B reuses that path for demo workspace creation and OWNER membership.
- Workspace switching and cache invalidation already live in the frontend auth store, so demo switching uses the same workspace-selection mechanism.
- Dashboard already had a pilot setup checklist and demo notice; Sprint 8B replaces local completion assumptions with a backend onboarding status endpoint.
- Existing product, inventory, lead, customer and order models are workspace-scoped; onboarding status uses lightweight workspace-wide existence checks rather than paginated list state.
- Existing demo docs and seed guidance were script-oriented; Sprint 8B documents the product demo workspace lifecycle separately.

## Product decisions
- New OWNER users get two paths: start with their own data or create/view a separate `Демо Sellora` workspace.
- Demo records are never inserted into a real workspace by default.
- Demo workspace identity is a UX label only; all security still comes from normal workspace membership and backend workspace scoping.

## First-run states
- **No workspace:** the authenticated user sees first-workspace creation plus `Переглянути демо Sellora`.
- **Empty real workspace:** Dashboard shows `Почнімо роботу з Sellora` and a compact checklist.
- **Partial real workspace:** checklist progress comes from actual workspace data.
- **Demo workspace:** a banner explains that values are synthetic and not real shop performance.

## Checklist logic
Completion is derived from actual workspace-wide data: configured workspace, active product+variant, positive inventory transaction, lead/customer presence, and order presence. Local storage may only be used later for collapse/dismiss UI state, not business completion.

## Onboarding API
`GET /api/v1/onboarding/status` is authenticated, requires an active workspace membership via `X-Workspace-ID`, is readable by OWNER/MANAGER/ANALYST, and returns progress, completed steps, role and suggested next action. The endpoint does not mutate data and does not accept a target workspace in the body.

## Demo workspace architecture
`POST /api/v1/workspaces/demo` reuses `WorkspaceService`; it creates or returns one active demo workspace for the user, creates OWNER membership only in that new demo workspace, and seeds a deterministic synthetic dataset. `PATCH /api/v1/workspaces/demo/deactivate` safely deactivates only eligible demo workspaces.

## Demo dataset catalog
The backend demo dataset contains synthetic DEMO leads, customers, products, variants, inventory transactions and orders. Phone values are non-routable `+000...` placeholders, Instagram usernames are synthetic, and no real addresses, emails, tokens, Meta IDs or Nova Poshta TTNs are included.

## RBAC behavior
- OWNER can create and deactivate the demo workspace and use all first-run actions.
- MANAGER receives operational checklist guidance but not OWNER-only settings/deactivation actions.
- ANALYST receives a read-only orientation and no active mutation CTA.

## Tenant isolation
Demo creation does not accept `workspace_id`, `tenant_id`, or a target workspace from the client. The generated workspace is normal tenant-scoped data, and real workspace metrics remain separate because all records are created with the demo workspace ID.

## Idempotency
Repeated demo creation returns the existing active demo workspace for the user when present. Duplicate clicks should not create multiple active demo workspaces.

## Rollback behavior
Demo generation is wrapped in the workspace service transaction; on failure the service rolls back and does not commit a partially usable active demo workspace.

## Empty-state coverage
The shared first-run checklist and demo actions cover Dashboard and no-workspace onboarding. Existing module empty states remain in place and are documented for Leads, Customers, Products, Inventory, Orders, Shipments, Advertising, Finance and Analytics in the pilot first-run guide.

## Desktop/mobile result
The first-run card, checklist and demo banner use compact responsive cards and existing Sellora semantic classes. Browser/mobile staging QA still must be executed on 1366×768, 375×812, 390×844, 430×932 and 768×1024 before unrestricted launch.

## Staging result
Local implementation and automated regressions are prepared. Staging execution requires staging OWNER/MANAGER/ANALYST accounts and a dedicated QA workspace; no production credentials or real customer data are required.

## Issues found
| ID | Severity | Area | Issue | Status |
|---|---|---|---|---|
| 8B-QA-001 | Observation | Browser QA | Device/browser staging QA remains a release-process step outside this local environment. | Documented |
| 8B-QA-002 | Observation | Demo depth | Advertising/finance/import deep validation remains assigned to 8C–8G. | Deferred |

## Fixes implemented
- Added workspace-scoped onboarding status API and tests.
- Added idempotent demo workspace creation/deactivation service flows and tests.
- Added Dashboard/no-workspace first-run UI, role-aware checklist, demo action and demo banner controls.
- Added Ukrainian and English localization keys for onboarding/demo copy.

## Remaining limitations
- Public self-service onboarding and billing remain out of scope.
- Live Instagram/Meta and Nova Poshta validation remain future sprint scope.
- Device/browser staging QA must run with staging credentials before broad pilot expansion.

## Sprint status
Sprint 8B — CONDITIONALLY APPROVED ⚠️ locally: core first-run/demo flows are implemented with backend tests and static regression coverage, but staging browser/mobile execution remains pending in this environment.

## Pilot recommendation
Controlled guided pilot remains GREEN ✅. Public production launch remains not approved.
