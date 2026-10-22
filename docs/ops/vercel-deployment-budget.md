# Sellora — контроль бюджету Vercel deployment (Issue #302)

**Policy owner:** Sellora frontend.
**Project:** `sellora-web-staging` (Vercel team `engine9rs-projects`, GitHub `eNgine9r/sellora`).
**Frontend root:** `frontend/`.
**Why:** Vercel Hobby rejected `POST /v13/deployments` with `api-deployments-free-per-day` after more than 100 deployments in a rolling 24-hour window.

## Auto-deployment contract

The supported config lives at `frontend/vercel.json`:

- **`main`** — allowed. Vercel continues to update the main Sellora staging address on reviewed changes.
- **`qa/preview-ready`** — allowed. One stable QA-only branch for a reviewed browser test snapshot.
- **Every other branch** — auto-deploy disabled via `"**": false`, including `ops/**`, `codex/**`, `fix/**`, `feat/**`, and third-party dependency branches. This rule also guards new branch names.
- Vercel evaluates matching branches so any matching `true` overrides a matching `false`. Do not add an unrelated `true` wildcard.
- Explicit, authenticated, manual deployment is a separate action and remains subject to the provider's quota.

**Important:** Vercel reads `vercel.json` from the project root of the commit being deployed. Long-lived branches that do **not** contain the policy may still make automatic previews. Rebase them onto the current `main` or avoid pushing them until their policy is updated; do not assume the config is an account-wide switch.

Official reference: https://vercel.com/docs/project-configuration/git-configuration

## Day-to-day release workflow

1. Work on `fix/*`, `feat/*`, `codex/*` or an `ops/*` branch with the policy inherited from `main`.
2. Run GitHub Actions CI on a PR to `main`; do not commit each modified file separately during normal development. Batch related changes into one reviewed commit when practical.
3. After code review and CI, intentionally move the validated candidate onto `qa/preview-ready` (a single commit/snapshot), then confirm the Vercel Preview SHA and status READY.
4. Perform actual browser QA (landing/login, leads, customers, orders, shipments, mobile, light/dark). Browser auth flows require a real existing user; do not create dummy accounts as a side effect.
5. Merge the approved PR into `main` and confirm its deployment status READY **and** that `sellora-web-staging.vercel.app` points to the merged commit.
6. Make no repeated changes to `qa/preview-ready` just to force a build. Use it once per QA candidate when needed. Budget target: no more than **15 deployments per day** in normal development. This target is an operational goal, not a platform guarantee.

## Regression / verification

- `node frontend/scripts/vercel-deployment-budget-regression.mjs` checks the allowlist and GitHub CI triggering.
- A skipped Vercel preview should generate **no deployment record** for the tested development branch, not merely a `SKIPPED` build status.
- After the quota resets, test **two successive commits** on a non-allowed branch (no new deployments), one QA branch commit (one READY Preview), then `main` (READY production-target staging update).
- Record the exact commit SHA, Vercel ID, state, alias, and timestamp. Verify quota count separately using the last 24 hours of Vercel deployment history.
- A branch policy is cost management, not a security control. Continue to review PR code and protect Vercel preview environment variables.

## Safe rollback

To restore Vercel's default automatic preview behavior, revert the policy file in a reviewed PR and merge to `main` after confirming this is intentional. **Do not** disable Git integration or remove the production `main` allow rule as a rollback method. Keep GitHub CI enabled.

For short-term QA when previews are restricted, use `qa/preview-ready`; do not remove the budget guard from the entire repository.

## Rollout status

Implementation and CI are tracked under Issue #302. Account-wide production settings, backend auth, environment secrets, RBAC, and the data layer are unchanged. Live QA proof must be recorded after provider quota recovery; static checks alone are not sufficient for acceptance.
