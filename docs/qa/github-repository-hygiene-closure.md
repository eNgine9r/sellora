# GitHub Repository Hygiene Closure

Date: 2026-07-18

Base commit: `6fa3e604cd2905ded8e10b5679bbf26e76227eab`

## Scope completed in this branch

- created one canonical `Sellora CI` workflow;
- removed three duplicate Sprint-named PR workflows after migrating their unique tests;
- converted storage readiness and restart-boundary preparation into explicit manual workflows;
- stabilized required check names;
- documented the branch-protection configuration that must be applied to `main`;
- audited the currently known open issue backlog;
- preserved all unresolved product/runtime issues instead of falsely closing them.

## Pull request backlog

At branch creation there were no open pull requests. PR #194 had already merged the endpoint-inventory correction and completed a green Sprint 8F.1 workflow run.

The only intended open PR after this branch is published is the repository-hygiene PR itself.

## Open issue decisions

### Issue #137 — staging browser login hangs

Decision: `KEEP_OPEN_BLOCKER`.

Reason:

- the acceptance criteria require hosted `/health`, valid synthetic OWNER login, invalid-login behavior, bounded frontend timeout handling, dashboard navigation and browser/mobile evidence;
- this workflow cleanup does not provide synthetic credentials or a complete hosted browser run;
- closing the issue without those results would be inaccurate.

Required next evidence:

- hosted backend `/health = 200`;
- valid synthetic OWNER login reaches `/dashboard`;
- invalid credentials return a bounded user-safe error;
- frontend does not hang indefinitely when Render is unavailable;
- full desktop/mobile matrix and workspace-switch checks pass.

Classification: critical runtime release blocker.

### Issue #132 — inventory row after product-variant archive

Decision: `KEEP_OPEN_PLANNED`.

Reason:

- acceptance requires atomic archive behavior, protection for reserved stock, retained transaction history and tenant-isolation/runtime evidence;
- CI cleanup does not change inventory archive behavior;
- no new implementation or runtime proof was added in this branch.

Classification: major inventory correctness/cleanup issue before broader pilot use.

### Issue #131 — net-profit formula alignment

Decision: `KEEP_OPEN_BLOCKER` for finance approval.

Reason:

- Order, Dashboard, Finance and Analytics must use one documented source of truth or clearly label intentional metric differences;
- this branch does not change or revalidate profit formulas;
- the issue must remain open until shipping, advertising, COD, payment, refund and return cost handling is regression-tested across all affected views.

Classification: major finance consistency release blocker.

## Issue closure policy

Issues may be closed only when one of the following is documented:

- a merged fixing PR and passing automated tests;
- hosted runtime/browser evidence satisfying the issue acceptance criteria;
- a verified duplicate with a replacement issue/PR;
- a product decision marking the work not planned, with rationale.

Age alone is not a closure reason.

## Branch audit policy

A remote branch is safe to delete only when:

- its PR is merged or closed;
- it has no active deployment dependency;
- it is not protected;
- it contains no unique unmerged work;
- it is not referenced by an active QA/runtime procedure.

Branch deletion was not performed in this repository-content PR. A separate GitHub settings/refs audit is required before deletion. Unknown branches must be retained.

## Supabase Preview

Supabase Preview is not a required Sellora CI gate unless every pull request receives a reliable preview database. A routinely skipped preview check must remain optional.

## Vercel

Vercel remains the required frontend deployment check. The expected project is `sellora-web-staging` with `frontend` as the application root. Platform-side duplicate-project cleanup requires separate Vercel settings evidence and is not performed by repository workflow changes.

## Branch protection

Status: `MANUAL_ACTION_REQUIRED` until verified through GitHub ruleset evidence.

Required checks:

- Sellora CI / backend-static
- Sellora CI / backend-focused
- Sellora CI / backend-full
- Sellora CI / postgresql-integration
- Sellora CI / frontend-production
- Sellora CI / security-and-tenant-isolation
- Vercel

Do not require manual runtime workflows or Supabase Preview.

## Remaining Sprint 8F.1 release gates

Repository CI cleanup does not approve the overall release. Remaining evidence:

- Render runtime commit equals the approved merge commit;
- runtime Alembic revision equals `202607180026`;
- desktop/mobile fulfillment browser QA;
- controlled real Nova Poshta TTN smoke test;
- restart durability;
- provider-first cleanup;
- environment and workspace provider writes returned to disabled state.

## Decision

```text
GitHub CI architecture: implemented in branch
Repository workflow duplication: removed in branch
Issue backlog: triaged and controlled
Branch cleanup: pending verified refs audit
Branch protection: MANUAL_ACTION_REQUIRED
Sprint 8F.1 overall release: NOT APPROVED
```
