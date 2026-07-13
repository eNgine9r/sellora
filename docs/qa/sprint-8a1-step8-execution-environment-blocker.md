# Sprint 8A.1 Step 8 — Execution Environment Blocker

## Result

GitHub-hosted Chromium can load the Vercel `/login` document at all required viewports, but requests to `https://sellora-api-staging.onrender.com/api/v1/auth/login` remain pending and time out.

## Evidence

- endpoint and method confirmed by the bounded login network probe;
- no HTTP response and no CORS response is received;
- 150-second login wait fails at all five viewports;
- credentials remain valid and both synthetic OWNER accounts are active;
- both synthetic OWNER accounts have active OWNER membership in Workspace A and Workspace B;
- no business fixtures were created by failed runs;
- no credentials or tokens were emitted into JSON/Markdown artifacts.

## Decision

GitHub-hosted Actions cannot be used as the final browser/mobile execution environment for Step 8 while this outbound route is unavailable. Final QA must run from the approved local Windows environment that can access Vercel and Render.

A one-command local PowerShell runner has been prepared. The resulting sanitized ZIP must be reviewed before the release decision can become APPROVED.
