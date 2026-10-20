# Sellora — verified current state

> **As of 2026-10-20, staging**. This file is a reconciled operational baseline, not proof of production readiness. Source: checked Vercel alias, Raspberry Docker health, Supabase read-only SQL, GitHub metadata, and non-networked tests.

## Current architecture

- Frontend: Next.js staging **https://sellora-web-staging.vercel.app/**, Vercel deployment `dpl_C8hiG9g6EUPJFuYXPLRgDRhhDHSy`, build `d05ab943d534806c1f5437afac30d0ce9d828bac`.
- Backend: FastAPI Docker on authorized Raspberry host `btc-radar`, image `sellora-backend:retire-legacy-20261020`; loopback bind `127.0.0.1:18000`, public HTTPS via Tailscale, Meta webhook worker running. Former Render runtime retired.
- Database: Supabase staging project `cznlsqgvwmccwkomjbeu`, Alembic revision **202610200038**.
- Authentication: HttpOnly Secure same-origin refresh cookie, server-side revocation, old `/auth/login` and `/auth/refresh` return 404, shared failed-login throttling enabled. Owner confirmed live sign-in. Existing Instagram token remains unchanged.
- Security: webhook table anonymous Data API exposure fixed; origin-specific CORS; frame-ancestors, anti-clickjacking and nosniff headers. **Strict script CSP, MFA, security log redaction remain open**.
- Direct: `Your Jewelry` Instagram connection **CONNECTED**, token not expired, four subscription fields, webhook has been received. 4 conversations and 37 messages were recorded during the read-only reconciliation; API-bounded historical completeness **not verified**.
- Sales: `Your Jewelry` has 504 orders; only 1 currently has a campaign_id. One fulfillment operation exists without a tracking number. Avoid assuming a completed live Nova Poshta shipment.
- Ads: 6 local campaigns, 5 daily metric rows, 0 provider `external_campaign_id` links; **no current `meta_ad_connections` row for Your Jewelry**. Real spend/CPA/ROAS cannot be asserted as synced.
- Data backup: encrypted `pg_dump -Fc` of staging created in protected local Raspberry storage, archive integrity checked and **full restore to disposable PostgreSQL 17 passed** (schema rev 038, 59 total Direct messages across all workspaces, 4 session rows, 51 tables at snapshot). Off-device backup, scheduled retention and separate key custody **not implemented**.
- Test evidence: **129 passed, 2 skipped** isolated/network-disabled backend tests in Direct proposal, fulfillment, Nova Poshta, order lifecycle, ad preview and attribution modules. These are not real API write/send tests.
- Provider controls: Instagram outbound send/auto-send/AI processing disabled. Do not enable, create real TTN, change campaigns, or submit conversions in test workflows.

## Discrepancies / risks

1. `main` README still describes Sprint 1.1 and says CRM features are not built. This contradicts deployed staging and the source code under multiple draft feature branches. README update belongs in separately reviewed release reconciliation.
2. PRs #234-250 (and other legacy drafts) have overlapping base branches. Some changes were **layered into Docker images or Vercel deployments directly** without merge to `main`. Never bulk-merge; first map each deployed layer to commit/patch.
3. Working tree on Raspberry has one modified cutover-plan file; do not overwrite it.
4. Historical Instagram history depth, Meta App Review/Live Mode, NP provider write readiness and authenticated end-to-end sale are not proven.
5. Supabase Security Advisor reports **RLS enabled without policies on many private tables**; this is not inherently public exposure, but function grants/security-definer routines require review.

## Safety rules

- Treat the exact deployed images and commit SHAs as runtime authority; do not replace them with stale `main` images.
- Back up before DDL; never restore a pre-Alembic-038 backend image after schema updates.
- Maintain feature-flagged rollback and unmodified Meta credentials.
- No reading or echoing raw customer messages, contact data, API tokens, or database passphrases into build logs or PR comments.
- Off-host backup requires a secure external destination and independent key custody, not a copy onto another unrelated lab service.
- Changes to real advertising, messages or shipping require an explicit owner confirmation and canary.

## Links

- [Public staging](https://sellora-web-staging.vercel.app/)
- [Original modernization PR #236](https://github.com/eNgine9r/sellora/pull/236)
- [Raspberry/OAuth cutover PR #237](https://github.com/eNgine9r/sellora/pull/237)
- [Direct history PRs #239-240](https://github.com/eNgine9r/sellora/pull/239)
- [Security session PRs #241-250](https://github.com/eNgine9r/sellora/pull/245)
- [Roadmap reconciliation issue #233](https://github.com/eNgine9r/sellora/issues/233)
