# Meta API Part 6 Readiness Plan

This is a planning document only. Part 6 Meta API work will be handled in separate dedicated sprints.

Meta Ads API is not active. No live OAuth, live Meta API calls, token storage, real Meta app credentials, real ad account IDs, or customer data transfer to Meta are implemented in Epic Sprint 5C.

## Guardrails for Part 6

- No live OAuth in 5C.
- No token storage in 5C.
- No Meta API calls in 5C.
- No real Meta app credentials in docs, tests, code, screenshots, or PR text.
- No real ad account IDs or business IDs.
- No customer/order payloads sent to Meta.
- Conversions API remains a separate future privacy/legal sprint.
- Advertising data remains manual/CSV until runtime/staging blockers are resolved.

## Recommended sequence

| Stage | Goal | Scope | Out of scope | Required Meta permissions | Backend changes | Frontend changes | Security requirements | QA requirements | Pilot-readiness gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Part 6.0 — Meta Developer App & Live OAuth Setup Checklist | Prepare the controlled Meta app setup before coding live OAuth. | Document app settings, redirect URI strategy, test users, review checklist, and staging-only validation. | No OAuth implementation, no token persistence, no API calls. | Document only; likely ads_read and business_management to be confirmed by Meta review. | Config checklist only. | Settings copy/checklist only. | No secrets in repo/docs; environment-only credentials. | Security review and staging checklist. | Checklist approved with synthetic workspace only. |
| Part 6.1 — Encrypted Token Storage & Connection Records | Add secure per-workspace connection records. | `meta_ad_connections` or equivalent, encrypted token reference, OWNER-only connect/disconnect. | No metrics sync, no Conversions API. | Confirmed permissions from 6.0. | Migration, encryption service, audit logs, RBAC. | OWNER-only connection UI. | Encrypted tokens, no raw token logs/responses, rotation path. | Migration runtime QA, token redaction tests, RBAC tests. | Safe staging token storage validated. |
| Part 6.2 — Read-only Meta Ads Insights Sync | Pull delivery metrics only into preview/staging sync. | Read-only insights fetch for spend, impressions, reach, clicks, messages if available. | No apply-sync without review, no customer/order data sent to Meta. | ads_read or approved equivalent. | Provider client, sync preview, rate-safe fetch. | Preview UI and conflict review. | No customer payloads, no raw Meta IDs in public UI. | Fake + sandbox/staging tests, no DB writes until approved. | Preview proves no manual/CSV overwrite. |
| Part 6.3 — Sync Runs, Rate Limits, Errors & Retry Policy | Make sync observable and recoverable. | Sync run records, retry policy, error reporting, rate-limit handling. | No Conversions API, no automatic attribution. | Same as 6.2. | Sync run persistence, worker-safe retry boundaries. | Admin status/error panel. | Redacted errors, no secrets in logs. | Rate-limit simulation, retry tests, staging dry-run. | OWNER can understand failures safely. |
| Part 6.4 — Staging QA & Pilot Gate | Decide whether live Meta sync can enter pilot. | Full staging QA, migration runtime QA, browser/mobile QA, rollback checklist. | No production rollout before gate. | Approved permissions only. | Operational runbook and rollback path. | Pilot-facing warnings and controls. | Synthetic/staging-only artifacts. | End-to-end staging with safe ad account. | Pilot gate signed off explicitly. |
| Part 7/8 — Conversions API, customer event privacy, hashing and consent | Future privacy-sensitive conversion events. | Legal/privacy-reviewed event design only after live read sync is stable. | Not part of Part 6. | Future CAPI permissions if approved. | Consent, hashing, event audit, opt-out. | Privacy copy and controls. | Legal/privacy review, no raw PII. | Dedicated privacy QA. | Separate approval required. |

## Sprint 6A design package

Meta Ads API is not active.

Sprint 6A prepares setup, security, OAuth, token storage, and QA design only. No live OAuth, no token storage, no live API calls, and no production sync were implemented.

Detailed Sprint 6A references:

- `docs/meta-developer-app-setup-checklist.md` — Meta Developer App and product-owner setup checklist.
- `docs/meta-permissions-plan.md` — least-privilege permissions plan for read-only insights first.
- `docs/meta-live-oauth-design.md` — future OWNER-only live OAuth flow and state validation contract.
- `docs/meta-token-storage-design.md` — future encrypted token storage requirements and table shape; no migration added in Sprint 6A.
- `docs/meta-connection-status-contract.md` — future connection status enum contract with UI-only localization.
- `docs/meta-audit-logging-design.md` — future Meta audit events and payload safety rules.
- `docs/meta-api-staging-qa-checklist.md` — staging QA and pilot gate checklist.

Part 6 Meta API work will be handled in separate dedicated sprints. Sprint 6B may only start after official Meta requirements are re-verified, staging domains are known, legal URLs are available, and a safe non-production workspace is ready.

## Sprint 6A.1 prerequisite package

Meta Ads API is not active.

Sprint 6A.1 prepares legal URLs, staging URL inventory, Meta App input pack, OAuth redirect URI planning, and environment variable planning only. No live OAuth, no token storage, no live API calls, and no production sync were implemented.

Sprint 6B should not begin implementation until the legal URLs, staging URL inventory, redirect URI plan, Meta Developer App inputs, and server-only environment variable plan are completed and reviewed.

## Sprint 6B — Meta encrypted connection foundation

Sprint 6B adds encrypted token storage infrastructure and connection records behind feature gates.

Meta Ads API is not sync-active.

Live sync, scheduled jobs, apply-sync, and Conversions API are not implemented.

Real OAuth validation requires staging URLs, legal review, Meta App setup, and safe PostgreSQL runtime migration QA.

Advertising remains feature-frozen and not pilot-ready.
