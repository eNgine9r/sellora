# Sellora MVP Readiness

## Current readiness decision

**READY FOR CONTROLLED GUIDED PILOT ✅**

This status is based on the completed Sprint 8A / 8A.1 staging release gate. It applies to the verified staging build and the tested MVP scope, not to unrestricted production launch or unvalidated external integrations.

## Core product readiness

- OWNER may start the mock connect flow, validate the mock callback, and simulate disconnect.
- MANAGER may view status only and may not connect or disconnect.
- ANALYST remains read-only/no-connect and may not connect or disconnect.
- Frontend hiding is not the protection boundary; service-level authorization rejects non-OWNER roles.
- Workspace context must be validated server-side for future live routes.

### Token safety shell

- Token-like values are masked with `mock_token_************abcd` style output or a fully redacted value.
- Secret-like payload fields are redacted before safe reporting.
- Safe diagnostics use a short one-way fingerprint, not a token value.
- Raw token-like values must never be returned to frontend DTOs, stored, logged, included in audit payloads, or included in string/repr output.
- Encryption persistence is not implemented in Sprint 4.12.

### Mock connection DTO contract

Safe mock DTOs may include `status`, `provider`, `workspace_id`, `connection_mode = mock`, `authorization_url`, `state_expires_at`, `connected = false`, `requires_live_setup = true`, `token_stored = false`, `live_api_enabled = false`, `message`, and user-safe `issues`. They must not include raw token fields, real ad account IDs, real business IDs, real Meta user IDs, customer/order data, or secret fields.

### Future audit event contract

Future audit events are `meta_ads_connect_started`, `meta_ads_connect_completed`, `meta_ads_connect_failed`, `meta_ads_disconnected`, `meta_ads_token_refreshed`, and `meta_ads_permission_missing`. Audit records may include workspace/user context and outcome, but must never include raw tokens, client secrets, cookies, customer PII, or customer/order payloads. Sprint 4.12 does not add a new audit table.

### Runtime-gated blockers remain

Sprint 4.10 runtime PostgreSQL migration QA remains pending, so Sprint 4.10 is not fully approved. Sprint 4.4 PostgreSQL runtime/staging/browser QA blockers, advertising CSV import staging QA, browser/mobile/theme QA, and workspace/cross-workspace runtime QA remain open. Meta sync remains not active, and manual/CSV remains the MVP advertising source.

## Sprint 4.13 — Meta Ads mock API boundary, route RBAC, and audit stubs

Sprint 4.13 keeps Meta Ads API inactive while preparing a backend-only, mock API boundary for future OAuth testing. The mock route prefix is `/integrations/meta-ads/mock`; it is disabled by default through `META_ADS_MOCK_OAUTH_API_ENABLED=false` and does not require any secret to remain inactive.

Mock API contract:

- `GET /integrations/meta-ads/mock/status` returns a safe not-active status with `provider=meta_ads`, `connection_mode=mock`, `connected=false`, `token_stored=false`, and `live_api_enabled=false`.
- `POST /integrations/meta-ads/mock/oauth/start` is OWNER-only, works only when the mock API feature gate is enabled, and returns only the obvious mock URL `https://mock.meta.local/oauth/authorize`.
- `POST /integrations/meta-ads/mock/oauth/callback` is OWNER-only, validates signed mock state, rejects invalid/expired/mismatched state, masks and discards synthetic token-like values, and returns only token-safety metadata.
- `POST /integrations/meta-ads/mock/disconnect` is OWNER-only and returns a non-persistent mock disconnect acknowledgement.

Route-level RBAC mirrors the Sprint 4.12 service contract: OWNER may start/callback/disconnect in mock mode when explicitly enabled for tests/dev; MANAGER and ANALYST are denied connect-like actions. Status viewing remains read-only. Frontend hiding is not the only protection.

Audit event stubs are non-persistent DTOs only. They document future events such as `meta_ads_mock_connect_started`, `meta_ads_mock_connect_callback_validated`, `meta_ads_mock_connect_denied`, `meta_ads_mock_disconnected`, and `meta_ads_mock_status_viewed`; no audit table or migration is added. Stub payloads must not include raw tokens, client secrets, cookies, customer/order data, or live account identifiers.

Safety guarantees for this sprint:

- no live Meta OAuth was implemented;
- no facebook.com OAuth redirect or graph.facebook.com API call was added;
- no real Meta OAuth URL, token storage, token input field, `meta_ad_connections` table, database migration, apply-sync, DB write, or production sync job was added;
- manual entry / CSV import remains the active MVP advertising source;
- Meta sync remains not active;
- Sprint 4.12 remains conditionally approved until frontend dependency recovery and browser/mobile QA are completed;
- Sprint 4.10 runtime PostgreSQL migration QA remains pending;
- Sprint 4.4 PostgreSQL runtime/staging/browser QA blockers remain open;
- advertising import is not pilot-ready.

## Sprint 4.14 — Advertising 4.x freeze and Part 5 handoff

Advertising is feature-frozen for now. Advertising is architecture-ready and locally validated, but Advertising is not pilot-ready and Advertising import is not pilot-ready.

Final Advertising 4.x status: **Advertising 4.x — architecture-ready / locally validated / feature-frozen / not pilot-ready**.

Meta Ads status: **Meta Ads API — mock/future-ready / not active**.

Manual/CSV remains the active source. Meta Ads API remains not active. Live OAuth/token storage/apply-sync are future work. Runtime/staging blockers are tracked separately in `docs/advertising-known-blockers.md`.

Part 5 may use Advertising data only as conditional manual/CSV source. Finance 5.x must not depend on live Meta OAuth, token storage, automatic attribution, apply-sync, production sync jobs, or unresolved runtime/staging QA.

Sprint 4.10 runtime PostgreSQL migration QA remains pending. Sprint 4.11 browser/mobile/theme QA remains pending. Sprint 4.12 browser/mobile QA remains pending. Sprint 4.4 PostgreSQL runtime/staging/browser QA blockers remain open.

## Finance 5A readiness note

Finance 5A is architecture-ready for MVP review as a read-only operational profit dashboard. It uses Sellora orders, order item costs, shipment/order shipping costs, and manual/CSV advertising metrics to calculate finance summaries.

Finance uses Advertising data only as conditional manual/CSV source until Advertising runtime/staging blockers are resolved.

Meta Ads API is not active.

Sellora Finance MVP is operational profit analytics, not full accounting software. Advertising and Advertising import remain not pilot-ready until the blocker registry is resolved.

## Finance 5B readiness note

Finance 5B adds manual expenses, refunds, discounts, fees, profit breakdown, and previous-period comparison. The feature is locally validated but the `finance_adjustments` migration still requires safe PostgreSQL runtime QA before production claims.

Sellora Finance is operational profit analytics, not full accounting or tax reporting. Advertising data remains a conditional manual/CSV source until runtime/staging blockers are resolved. Meta Ads API is not active.

## Epic Sprint 5C — Finance stabilization readiness

Finance 5.x is implementation-ready and locally validated, with `/finance` UX stabilized as far as static/local validation allows. It is not pilot-ready until browser/mobile QA, staging QA, and PostgreSQL runtime migration QA are completed.

Finance adjustments migration has passed static Alembic chain validation, but PostgreSQL runtime migration QA remains pending until tested against a safe staging/test database.

Advertising data remains a conditional manual/CSV source until runtime/staging blockers are resolved. Meta Ads API is not active. Part 6 Meta API work will be handled in separate dedicated sprints.

## Sprint 6A — Meta live readiness design status

Meta Ads API is not active.

Sprint 6A prepares setup, security, OAuth, token storage, and QA design only. No live OAuth, no token storage, no live API calls, and no production sync were implemented.

Advertising remains feature-frozen and not pilot-ready. Finance 5.x remains locally validated with runtime migration QA and browser/mobile QA blockers tracked separately.

## Sprint 6A.1 — Meta OAuth prerequisite readiness

Meta Ads API is not active.

Sprint 6A.1 prepares legal URLs, staging URL inventory, Meta App input pack, OAuth redirect URI planning, and environment variable planning only. No live OAuth, no token storage, no live API calls, and no production sync were implemented.

Legal pages are MVP drafts and require legal review before production launch or Meta App Review submission. Advertising remains feature-frozen and not pilot-ready.

## Sprint 6B — Meta encrypted connection foundation

Sprint 6B adds encrypted token storage infrastructure and connection records behind feature gates.

Meta Ads API is not sync-active.

Live sync, scheduled jobs, apply-sync, and Conversions API are not implemented.

Real OAuth validation requires staging URLs, legal review, Meta App setup, and safe PostgreSQL runtime migration QA.

Advertising remains feature-frozen and not pilot-ready.

## Sprint 6C — Meta read-only discovery and sync-preview foundation

Sprint 6C adds read-only discovery and sync-preview foundations only.

Meta Ads API is not sync-active.

No scheduled sync jobs, no apply-sync, no ad_metrics writes, no customer/order data transfer, and no Conversions API were implemented.

Manual/CSV remains the active Advertising source.

Advertising remains feature-frozen and not pilot-ready.

Runtime/staging validation is still required before any live sync claim.

## Sprint 6D — Live read-only Meta foundation and staging validation gate

Sprint 6D adds live read-only client foundation and staging validation gate only.

Meta Ads API is not sync-active.

No scheduled sync jobs, no apply-sync, no ad_metrics writes, no ad_campaigns writes, no customer/order data transfer, and no Conversions API were implemented.

Manual/CSV remains the active Advertising source.

Advertising remains feature-frozen and not pilot-ready.

Real staging OAuth validation, runtime migration QA, Meta App setup, legal review, and browser/mobile QA are still required before pilot-ready claims.

## Sprint 6E — Runtime/Staging QA gate

Sprint 6E is a QA/risk-closure sprint for the existing Meta Ads foundations.

Result: **BLOCKED** because confirmed safe non-production PostgreSQL runtime migration QA, real Meta OAuth staging validation, Meta Developer App setup, legal review, staging URLs, role-specific test accounts, safe connected workspace validation, and browser/mobile staging smoke QA were unavailable.

Meta Ads API is not production sync-active. Advertising remains feature-frozen and not pilot-ready. No scheduled sync jobs, no apply-sync, no ad_metrics writes, no ad_campaigns writes, no customer/order data transfer, and no Conversions API were implemented.

## Sprint Admin Roles & Users

Sprint Admin Roles & Users adds multi-workspace MVP, workspace switcher, workspace settings, and team management. OWNER can create and manage workspace/team. MANAGER and ANALYST cannot manage workspace/team. User can belong to multiple workspaces. Deactivation is workspace-level through workspace_user.is_active=false. Email invitations, password reset, billing, super admin, and audit log UI remain out of scope.

## Topbar profile/mobile overlay cleanup

Workspace and user actions were moved into safer profile/mobile overlay menus to avoid header overflow and clipped dropdowns.

## Sprint 7A SaaS Admin Workspace QA

Sprint 7A adds a SaaS admin QA report and stabilizes the no-workspace onboarding path so authenticated users without active memberships can create their first workspace instead of being redirected as unauthenticated. Staging runtime QA remains pending where network access is blocked.

## Sprint 7A.1 manual staging QA closure

Sprint 7A.1 documents the remaining manual staging QA closure requirements for SaaS admin workspace flows. Full approval is blocked until staging role/workspace/team/mobile QA can be completed from an environment that can reach the Vercel and Render staging URLs.

## Sprint 7F runtime migration closure

Sprint 7F completed Alembic inventory, migration risk review, local backend/frontend validation, and a runtime migration attempt against the provided PostgreSQL endpoint. Full runtime approval remains blocked because the database host could not be resolved from this validation container, so `alembic upgrade head` and runtime schema verification did not execute.

## Sprint 7B core flow UX stabilization

Sprint 7B improves Lead → Customer → Order → Payment → Shipment → Profit clarity with Ukrainian loading/empty/error states, customer purchase context, order payment/profit/shipment helpers, dashboard period explanation, and no new database migrations. Manual mobile/browser QA remains recommended before full release approval.

## Sprint 7C dashboard owner experience

Dashboard owner experience is conditionally approved. The page now explains selected-period KPI values, missing profit/ad data, sales funnel state, fulfillment work, inventory attention, and recent-orders scope using existing workspace-scoped data. Manual browser/mobile QA remains recommended before full release approval.

## Sprint 7D mobile UX / PWA MVP

Mobile UX/PWA MVP is conditionally approved. The app now has bottom quick navigation, better mobile cards for key CRM/order lists, owner-facing manifest metadata, and documented no-private-data caching policy. Manual mobile/PWA install QA remains required before full approval.

## Sprint 7E RBAC, tenant isolation & security QA

Sprint 7E is conditionally approved. Backend security tests now cover endpoint inventory, OWNER/MANAGER/ANALYST guards, inactive/no-membership denial, tenant list/detail/update/archive IDOR for representative core flows, nested order/finance ownership checks, and finance aggregation scoping. A Lead assignment bug was fixed so inactive workspace memberships cannot be assigned to leads.

Manual browser/mobile workspace-switch race-condition QA and broader audit-log standardization remain follow-ups. Sprint 7F runtime migration QA remains blocked separately.

## Sprint 7E.1 security closure readiness

- Sprint 7E and Sprint 7E.1 are approved from automated security and CI validation.
- Request-body workspace injection is covered by create, update and nested cross-workspace negative tests.
- Frontend deterministic install is restored through the tracked npm lockfile and clean `npm --prefix frontend ci` validation.
- Workspace switching now cancels active React Query requests, invalidates workspace-scoped data after switching, and logout clears the private query cache.
- Endpoint inventory primary classifications reconcile to the 153-route FastAPI inventory.
- Sprint 7F runtime PostgreSQL migration QA remains a separate infrastructure blocker until an approved runtime environment is available.

## Sprint 8A staging release gate

Sprint 8A is blocked, and the pilot release decision is **RED — NO-GO**. A safe staging release-gate runner and checklist now exist, but the local validation container could not reach the Vercel frontend or Render backend because both staging URLs returned proxy `CONNECT tunnel failed, response 403`. OWNER/MANAGER/ANALYST staging credentials were not available, runtime database revision was not verified, and the synthetic core E2E order flow was not executed.

Next readiness step: rerun Sprint 8A from a network with staging access and secure synthetic role credentials after Sprint 7F runtime migration compatibility is safely resolved or independently verified.

## Sprint 8A.1 staging E2E closure attempt

Sprint 8A.1 remains blocked and the pilot release decision remains **RED — NO-GO**. The existing runner was reused and extended for 8A.1 artifact fields, but this environment still cannot reach Vercel/Render staging URLs, secure role credentials and `STAGING_TEST_WORKSPACE_ID` are absent, runtime Alembic revision is unverified, and controlled-write E2E/browser-mobile QA did not execute.

## Sprint 8B — Demo Data & First-run Experience

Sprint 8B adds workspace-scoped onboarding status, role-aware first-run guidance and an isolated `Демо Sellora` workspace flow. Controlled guided pilot remains GREEN for monitored staging/pilot use; unrestricted public production launch remains not approved.

## Sprint 8C import readiness update

Import Center now has explicit pilot contracts for supported `.xlsx`/`.csv` formats, file limits, duplicate policy, dry-run-before-execute gating, workspace-switch state clearing, and PII-safe handling guidance. Full Sprint 8C approval still requires staging import gates and browser/mobile QA with synthetic data.

## Sprint 8D operations readiness update

Orders, inventory and local shipments now have documented operational invariants, explicit order transition rules, reservation delta tests, Issue #134 inventory visibility policy, and one-active-shipment pilot coverage. Full Sprint 8D approval still requires staging controlled-write and browser/mobile evidence.

## Sprint 8E Nova Poshta readiness update

Nova Poshta integration code is conditionally ready for a controlled staging pilot. Provider writes are protected by a deployment capability, verified workspace connection, complete sender configuration, and explicit OWNER activation; managers receive only a safe readiness response without credentials or sender references. General availability remains blocked until the controlled real-provider validation, browser/mobile QA, and operational rollback evidence in the staging checklist are complete.

## Sprint 8F.1 fulfillment readiness update — 2026-07-18

Repository implementation now includes a durable fulfillment operation journal and existing-order fulfillment endpoints. MVP readiness remains **not approved for public unrestricted production launch** until PostgreSQL CI, runtime deployment, browser QA, and controlled Nova Poshta smoke evidence are completed and documented.

## Sprint 8F.1 consolidation readiness update — 2026-07-18

Fulfillment now has a single canonical persistence model in the repository: `order_fulfillments`. MVP readiness remains blocked until migration `202607180026`, seeded PostgreSQL concurrency checks, deployment evidence, browser QA, and one controlled Nova Poshta smoke test are complete.
