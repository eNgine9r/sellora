# Advertising Known Blockers Registry — Sprint 4.14

Advertising 4.x is **architecture-ready / locally validated / feature-frozen / not pilot-ready**. Runtime/staging QA is intentionally not executed in Sprint 4.14 and is tracked here instead.

Meta Ads API status: **mock/future-ready / not active**. Active Advertising data source: **manual entry / CSV import**.

## Blocker severity guide

- **High**: blocks pilot readiness and requires runtime/staging validation before production claims.
- **Medium**: blocks full UX confidence, browser/mobile/theme approval, or conditional sprint approval.
- **Low**: documentation-only limitation or future roadmap dependency.

## Registry

| ID | Title | Severity | Affected module | Why it matters | Current status | Required inputs | Required validation steps | Owner / future sprint | Blocks pilot readiness | Blocks Part 5 |
|---|---|---:|---|---|---|---|---|---|---|---|
| B-ADV-001 | Sprint 4.4 PostgreSQL runtime migration QA pending | High | Advertising DB runtime | Confirms migrations run on a safe PostgreSQL runtime and can be downgraded without data loss. | Pending / not executed | Safe PostgreSQL test DB, non-production credentials, migration command access | Run `alembic upgrade head`, `alembic downgrade -1`, `alembic upgrade head`; verify existing rows and indexes. | Future runtime QA sprint | Yes | No, if Part 5 treats Advertising as conditional manual/CSV source |
| B-ADV-002 | Sprint 4.4 staging/browser attribution QA pending | High | Advertising attribution UX | Confirms manual lead/order campaign attribution is understandable and works in staging browser flows. | Pending / not executed | Staging frontend/backend, synthetic workspace, OWNER/MANAGER test user | Create campaigns, leads, orders; assign campaign attribution; verify tables/details/reporting. | Future staging QA sprint | Yes | Partially; attributed revenue/profit must be used with caution |
| B-ADV-003 | Advertising CSV import staging QA pending | High | Import Center / Advertising metrics | Confirms CSV import validates and writes advertising metrics safely in staging. | Pending / not executed | Staging Import Center, synthetic CSV, clean test workspace | Dry-run, validate row errors, execute import, verify metrics/reporting, verify no cross-workspace leakage. | Future staging QA sprint | Yes | Partially; CSV ad metrics are conditional until this passes |
| B-ADV-004 | Browser/mobile/theme QA pending | Medium | Advertising UI | Confirms responsive layout, light/dark readability, and mobile usability for real shop owners. | Pending / not executed | Browser/device matrix or Playwright setup, staging/dev frontend | Check `/advertising`, `/settings/import`, lead/order campaign attribution surfaces at 375px, 390px, 768px, desktop, light/dark. | Future UX QA sprint | Yes | No |
| B-ADV-005 | Workspace/cross-workspace runtime QA pending | High | Multi-tenant Advertising runtime | Confirms campaign/metric/import/attribution data does not leak between workspaces in runtime flows. | Pending / not executed | Two synthetic workspaces, users with different roles, staging/runtime backend | Verify every campaign, metric, attribution, import and preview query is scoped by `workspace_id`. | Future tenant QA sprint | Yes | No, if Part 5 uses existing workspace-scoped repositories cautiously |
| B-ADV-006 | Sprint 4.10 PostgreSQL runtime migration QA pending | High | External identity migration draft | Confirms nullable external identity/source fields migrate safely on PostgreSQL. | Pending / not executed | Safe PostgreSQL test DB and Alembic access | Run upgrade/downgrade/upgrade; verify nullable-first fields and indexes. | Future migration QA sprint | Yes for Meta readiness; no for manual Advertising | No for Finance MVP if Meta sync remains inactive |
| B-ADV-007 | Sprint 4.11 browser/mobile/theme QA pending | Medium | Meta Ads not-active UX | Confirms feature-gated Meta Ads not-active messaging is not confusing on devices/themes. | Pending / not executed | Browser/device matrix or Playwright setup | Verify not-active status, disabled CTA, no token input, no fake account presented as real. | Future UX QA sprint | No for manual Advertising; yes for Meta pilot UX | No |
| B-ADV-008 | Sprint 4.12 browser/mobile QA pending | Medium | Mock OAuth UX copy / readiness card | Confirms mock OAuth/future-copy remains clearly disabled and not presented as live connection. | Pending / not executed | Browser/device matrix or Playwright setup | Verify no live OAuth link, no token input, disabled CTA copy, no missing i18n. | Future UX QA sprint | No for manual Advertising; yes for Meta connection UX | No |
| B-ADV-009 | Advertising import not pilot-ready | High | Advertising import | Import can affect reporting and owner trust, so it needs staging QA and row-level validation confidence. | Open | Synthetic staging import dataset, staging workspace | Complete B-ADV-003 plus regression review and import rollback/cleanup plan. | Future import QA sprint | Yes | Partially; imported ad spend should be treated as conditional |
| B-ADV-010 | Live Meta OAuth/API/token storage not implemented | Low | Meta Ads integration | Live Meta integration is intentionally future work; current implementation is mock/future-ready only. | Not implemented by design | Dedicated future Meta OAuth sprint, encryption/storage design, Meta app credentials in secure environment | Implement encrypted token persistence, live OAuth, permission review, audit logs, and staging security QA in future. | Future Meta integration sprint | No for manual Advertising; yes for live Meta pilot | No for Finance MVP |

## Freeze impact

Advertising remains **not pilot-ready** until pilot-readiness blockers are closed. Part 5 may proceed only if it treats Advertising data as a **conditional manual/CSV source** and does not depend on live Meta sync, automatic attribution, apply-sync, or unresolved staging/runtime QA.
