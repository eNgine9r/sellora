# Sprint 8B — Staging Closure Evidence

## Final decision

**Sprint 8B — APPROVED ✅**

**Controlled guided pilot with first-run/demo — GREEN ✅**

This approval applies to the verified staging deployment and the controlled guided pilot boundary. It does not approve unrestricted public production launch, billing, public self-service signup, live Meta/Instagram writes, or uncontrolled Nova Poshta provider actions.

## Verified deployments

- Backend staging: Render commit `2c9fe282a99cb06b4d76239a09f1dc3c1672a112`.
- Frontend staging: Vercel commit `f61913cfb1850146a9dc66067274792280fb67de`.
- Runtime Alembic revision: `202607130021`.
- Packaged Alembic head: `202607130021`.
- FastAPI runtime verified the required Sprint 8B routes from generated OpenAPI:
  - `GET /api/v1/onboarding/status`;
  - `POST /api/v1/workspaces/demo`;
  - `PATCH /api/v1/workspaces/demo/deactivate`.

## Execution mechanism

Sprint 8B reused the established Sprint 8A.1 GitHub Actions + Python Playwright browser runner approach. The QA-only runner lived in PR #141 and was closed without merge after the evidence was collected.

Final workflow evidence:

- GitHub Actions run: `29283862006`;
- artifact: `sellora-sprint-8b-staging-closure-29283862006`;
- final decision: `PASS`;
- passed checks: `181`;
- failed checks: `0`;
- unique failures: `0`;
- screenshots: `91`;
- captured network events: `1,142`.

## Browser and viewport matrix

The following viewport configurations passed in both light and dark themes:

| Viewport | Result |
|---|---|
| 1366 × 768 | PASS |
| 375 × 812 | PASS |
| 390 × 844 | PASS |
| 430 × 932 | PASS |
| 768 × 1024 | PASS |

The matrix covered responsive layout, overflow, first-run checklist, demo loading, demo banner, honest empty states, workspace switching and deactivation controls.

## OWNER scenarios

- Empty real workspace displays the backend-derived first-run checklist.
- Checklist progress matches actual workspace data.
- Demo creation loading state is visible.
- A double click emits exactly one demo `POST`.
- Repeated runtime demo creation returns the same active demo workspace ID.
- Demo workspace uses a separate workspace ID.
- Demo banner appears immediately after successful creation.
- Real workspace data remains unchanged.
- Demo workspace is safely deactivated after confirmation.

## MANAGER scenarios

- Operational onboarding guidance is displayed.
- OWNER-only settings/demo management CTA is absent.
- Demo management API returns `403` safe denial.

## ANALYST scenarios

- Read-only orientation is displayed.
- Mutation CTA is absent.
- Direct mutation API request returns `403`.

## Demo provenance and deactivation safety

Demo eligibility is based on immutable server-side provenance recorded through the `DEMO_WORKSPACE_CREATE` audit event. Workspace name, slug and record contents are not accepted as security eligibility criteria.

Verified behavior:

- a normal workspace cannot use the demo deactivation endpoint;
- MANAGER and ANALYST cannot deactivate an OWNER demo workspace;
- only an eligible audit-provenance demo workspace can be deactivated;
- the deactivation confirmation dialog is shown before the request.

## Idempotency and rollback

- Browser duplicate-click protection emitted one demo POST.
- Two subsequent runtime demo POST requests returned the same workspace ID.
- Backend rollback regression passed in the deployment pipeline.
- No partially generated active demo workspace remained after the controlled failure scenario.

## Demo dataset scope

Sprint 8B uses the approved **core demo dataset**:

| Entity | Verified count |
|---|---:|
| Leads | 6 |
| Customers | 4 |
| Products | 6 |
| Inventory records | 6 |
| Inventory transactions | 6 |
| Orders | 5 |
| Shipment drafts | 0 |
| Advertising campaigns | 0 |
| Advertising metrics | 0 |
| Finance adjustments | 0 |

Shipments, Advertising and Finance retain truthful empty or order-derived states. The UI does not imply that absent provider, advertising or adjustment data exists.

## Workspace isolation and cache behavior

The closure verified real → demo → real transitions for every viewport/theme configuration.

Must-pass evidence:

- selected workspace ID in local storage matched the expected workspace;
- `/leads` requests used the matching `X-Workspace-ID`;
- the real workspace displayed only its synthetic QA marker and no DEMO leads;
- the demo workspace displayed DEMO leads and no real-workspace marker;
- stale cross-workspace DOM records: `0`.

A staging-discovered React Query tenant-transition race was fixed in PR #143. Workspace switching now cancels pending queries and destroys the previous tenant cache before exposing the next workspace ID.

## Network and security result

| Check | Result |
|---|---:|
| Core HTTP 500 responses | 0 |
| Runtime exceptions | 0 |
| Cross-workspace responses | 0 |
| Meta provider requests | 0 |
| Nova Poshta provider requests | 0 |
| Credential/token exposure | 0 |
| Authorization headers stored in evidence | 0 |

Passwords, tokens, authorization headers and API keys were suppressed from console and artifact evidence.

## Synthetic cleanup

After closure:

- 7 temporary Sprint 8B workspaces were deactivated;
- 11 temporary workspace memberships were deactivated;
- 7 no-workspace synthetic users were deactivated;
- active synthetic demo workspaces: 0;
- QA marker leaks into the real `Your Jewelry` workspace: 0;
- `Your Jewelry` remained active with its existing three active memberships.

## Closed issues

| ID | Severity | Issue | Resolution |
|---|---|---|---|
| 8B-QA-001 | Major | Browser/mobile staging QA missing | Closed by 5-viewport × 2-theme Playwright matrix |
| 8B-SEC-001 | Major | Demo eligibility depended on slug/name heuristics | Closed by server-side audit provenance |
| 8B-UX-001 | Major | Stale demo records after workspace switch | Closed by tenant cache destruction before workspace transition |
| 8B-DATA-001 | Observation | Demo dataset depth was ambiguous | Closed by explicit core dataset contract and truthful empty states |

No Critical or Major Sprint 8B issue remains open.

## Pilot recommendation

```text
Existing controlled pilot baseline: GREEN ✅
Sprint 8B first-run/demo features: GREEN ✅
Sprint 8B: APPROVED ✅
Unrestricted public production launch: NOT APPROVED
```

The next planned product stage is **Sprint 8C — Import Center Pilot Hardening**.
