# Sprint 10 final Meta runtime closure preflight

Date: 2026-07-18.

## Authoritative source limitations

This container has no configured `origin` remote, so GitHub API/source-of-truth checks, open PRs, Sellora CI, Render health, Vercel deployment status, and runtime Meta environment values could not be queried from the checkout. The requested authoritative main merge commit is `83ff2bfe36e4edebddfb2944d5577a4032033241`; the local branch started from commit `b6515c4` and Alembic head `202607180028` before this closure work.

## Local baseline verified

- Current branch created for closure: `fix/sprint-10-final-meta-runtime-closure`.
- Local Alembic head before changes: `202607180028`.
- Existing Meta foundation modules reused: `InstagramConnection`, `MetaOAuthState`, `MetaWebhookEvent`, `MetaMessageOperation`, `MetaInstagramClient`, `InstagramConnectionService`, `InstagramOAuthService`, `InstagramInboundMessageService`, and `InstagramOutboundMessageService`.
- No duplicate Direct or Instagram domain models were introduced.

## Official Meta documentation rechecked

- Instagram API with Instagram Login Messaging API: manager sends to users who messaged the professional account.
- Instagram webhook setup: webhook subscriptions and raw request validation are server responsibilities.
- Meta messaging policy and Human Agent feature: standard 24-hour messaging window and HUMAN_AGENT manual response extension up to 7 days where approved.

## Implementation closure inventory

- OAuth closure must replace storing authorization code as token with server-side token exchange and account/permission validation.
- Webhook closure must add PostgreSQL event processor and inbound service integration outside the request transaction.
- Outbound closure must separate operation persistence from provider HTTP send and preserve failure/reconciliation state.
- Direct UI must stop using production hardcoded conversations and load workspace-scoped backend API data.
