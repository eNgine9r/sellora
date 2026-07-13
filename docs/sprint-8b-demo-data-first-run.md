# Sprint 8B — Demo Data & First-run Experience

## Scope
Sprint 8B adds real first-run guidance, workspace-scoped onboarding status, and a separate synthetic demo workspace flow. It does not add public self-service signup, billing, live Meta/Instagram sync, Nova Poshta TTN creation, migrations, or unrestricted production launch.

## Pre-implementation inventory
- Workspace creation already lives in `WorkspaceService` and `WorkspaceRepository`; Sprint 8B reuses that path for demo workspace creation and OWNER membership.
- Workspace switching and cache handling live in the frontend auth store, so demo switching uses the same workspace-selection mechanism with a tenant-boundary cache reset.
- Dashboard already had a pilot setup checklist and demo notice; Sprint 8B replaces local completion assumptions with a backend onboarding status endpoint.
- Existing product, inventory, lead, customer and order models are workspace-scoped; onboarding status uses lightweight workspace-wide existence checks rather than paginated list state.
- Existing demo docs and seed guidance were script-oriented; Sprint 8B documents the product demo workspace lifecycle separately.

## Product decisions
- New OWNER users get two paths: start with their own data or create/view a separate `Демо Sellora` workspace.
- Demo records are never inserted into a real workspace by default.
- Demo workspace security eligibility is established by immutable server-side `DEMO_WORKSPACE_CREATE` audit provenance, not by workspace name, slug or record contents.
- The first demo scope is intentionally the core operational dataset: CRM + Catalog + Inventory + Orders.

## First-run states
- **No workspace:** the authenticated user sees first-workspace creation plus `Переглянути демо Sellora`.
- **Empty real workspace:** Dashboard shows `Почнімо роботу з Sellora` and a compact checklist.
- **Partial real workspace:** checklist progress comes from actual workspace data.
- **Demo workspace:** a banner explains that values are synthetic and not real shop performance.

## Checklist logic
Completion is derived from actual workspace-wide data: configured workspace, active product+variant, positive inventory transaction, lead/customer presence, and order presence. Local storage is not used as the business completion source.

## Onboarding API
`GET /api/v1/onboarding/status` is authenticated, requires an active workspace membership via `X-Workspace-ID`, is readable by OWNER/MANAGER/ANALYST, and returns progress, completed steps, role and suggested next action. The endpoint does not mutate data and does not accept a target workspace in the body.

## Demo workspace architecture
`POST /api/v1/workspaces/demo` reuses `WorkspaceService`; it creates or returns one active demo workspace for the user, creates OWNER membership only in that new demo workspace, records server-side provenance and seeds a deterministic synthetic dataset. `PATCH /api/v1/workspaces/demo/deactivate` safely deactivates only eligible provenance-backed demo workspaces.

## Demo dataset catalog
The backend demo dataset contains synthetic DEMO leads, customers, products, variants, inventory transactions and orders. Phone values are non-routable `+000...` placeholders, Instagram usernames are synthetic, and no real addresses, emails, tokens, Meta IDs or Nova Poshta TTNs are included.

Verified core counts:

- 6 leads;
- 4 customers;
- 6 products and active variants;
- 6 inventory records and 6 stock transactions;
- 5 orders;
- 0 shipment drafts;
- 0 advertising campaigns/metrics;
- 0 finance adjustments.

Shipments, Advertising and Finance show truthful empty or order-derived states for the missing demo entities.

## RBAC behavior
- OWNER can create and deactivate the demo workspace and use all first-run actions.
- MANAGER receives operational checklist guidance but not OWNER-only settings/deactivation actions; demo management requests return `403`.
- ANALYST receives a read-only orientation, no active mutation CTA and `403` for direct mutation requests.

## Tenant isolation
Demo creation does not accept `workspace_id`, `tenant_id`, or a target workspace from the client. All generated records use the new demo workspace ID. Workspace switching cancels pending queries and destroys the previous tenant cache before the next workspace ID is exposed.

Runtime staging evidence confirmed:

- real workspace API and DOM contained the real synthetic marker and no DEMO leads;
- demo workspace API and DOM contained DEMO leads and no real marker;
- stale cross-workspace records across all viewport/theme configurations: 0.

## Idempotency
Repeated demo creation returns the existing active provenance-backed demo workspace. Browser duplicate-click testing emitted exactly one POST, and two later runtime POST requests returned the same demo workspace ID.

## Rollback behavior
Demo generation is wrapped in the workspace service transaction. The controlled failure regression passed in CI and left no partially generated active demo workspace.

## Empty-state coverage
The shared first-run checklist and demo actions cover Dashboard and no-workspace onboarding. Existing module empty states remain in place for Leads, Customers, Products, Inventory, Orders, Shipments, Advertising, Finance and Analytics. Demo-specific Shipments, Advertising and Finance states were reviewed in the staging matrix.

## Browser/mobile staging result
Browser QA passed in both light and dark themes for:

- 1366 × 768;
- 375 × 812;
- 390 × 844;
- 430 × 932;
- 768 × 1024.

Final evidence: 181 checks passed, 0 failed, 91 screenshots and 1,142 captured network events.

## Deployment result
- Render backend commit: `2c9fe282a99cb06b4d76239a09f1dc3c1672a112`.
- Vercel frontend commit: `f61913cfb1850146a9dc66067274792280fb67de`.
- Runtime and packaged Alembic revision: `202607130021`.
- FastAPI OpenAPI route verification passed for onboarding and demo lifecycle routes.

## Security/network result
- Core HTTP 500 responses: 0.
- Runtime exceptions: 0.
- Cross-workspace responses: 0.
- Meta requests: 0.
- Nova Poshta requests: 0.
- Credential/token exposure: 0.

## Issues found and closed
| ID | Severity | Area | Issue | Status |
|---|---|---|---|---|
| 8B-QA-001 | Major | Browser QA | Browser/mobile staging evidence was missing. | Closed |
| 8B-SEC-001 | Major | Demo provenance | Name/slug heuristics were insufficient for deactivation eligibility. | Closed with audit provenance |
| 8B-UX-001 | Major | Workspace switch | Demo rows could remain visible during a tenant transition. | Closed with cache reset before workspace switch |
| 8B-DATA-001 | Observation | Demo depth | Shipment/advertising/finance demo scope was ambiguous. | Closed with core dataset contract |

## Fixes implemented
- Added workspace-scoped onboarding status API and tests.
- Added idempotent demo workspace creation/deactivation with server-side provenance and rollback coverage.
- Added Dashboard/no-workspace first-run UI, role-aware checklist, demo action and demo banner controls.
- Added Ukrainian and English localization keys for onboarding/demo copy.
- Hardened tenant cache clearing during workspace switching.
- Added Render build/startup verification for required Sprint 8B routes.
- Completed controlled API/browser/mobile staging closure and synthetic cleanup.

## Remaining limitations
- Public self-service onboarding and billing remain out of scope.
- Live Instagram/Meta and unrestricted Nova Poshta actions remain outside this approval.
- Import Center pilot hardening remains assigned to Sprint 8C.
- Public production launch remains not approved.

## Closure evidence
See `docs/sprint-8b-staging-closure.md`.

## Sprint status
**Sprint 8B — APPROVED ✅**

## Pilot recommendation
**Controlled guided pilot with first-run/demo — GREEN ✅**

Proceed to **Sprint 8C — Import Center Pilot Hardening**.
