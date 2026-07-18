# Sprint 10 Meta pre-implementation audit

Date: 2026-07-18.

## Authoritative preflight limitations

This local checkout has no configured GitHub remote, so `origin/main`, open PRs, GitHub Actions, Render, and Vercel status cannot be verified from the container. The local Git head before Sprint 10 work was `0676e4c` and the local Alembic head was `202607180027`.

## Official Meta documentation checked

- Meta Instagram Messaging webhooks documentation: messages and messaging postback webhook notifications.
- Meta Instagram API with Instagram Login messaging API documentation: sending messages from an Instagram Professional account.
- Meta Messenger/Instagram messaging policy documentation: standard 24-hour response window and HUMAN_AGENT manual response extension.

## Existing implementation inventory

- `DirectConversation`, `DirectMessage`, `AIAnalysis`, `AISuggestion`, `AIActionDraft`, `AIWorkspaceSettings`, `AIUsageEvent`, and `AIFeedback` exist in `backend/app/models/ai_direct.py`.
- Workspace membership and RBAC use `X-Workspace-ID`, `require_min_role`, and `require_roles` dependencies.
- The frontend authenticated API client is `frontend/src/services/api.ts` and injects workspace headers from authenticated state.
- Existing Meta Ads integration code provides a token crypto utility and read-only/sync-preview patterns under `backend/app/integrations/meta_ads/`.
- Existing webhook infrastructure for Instagram messaging did not exist before this Sprint 10 implementation.
- Existing background-task infrastructure for durable Instagram webhook workers was not present; Sprint 10 adds a PostgreSQL event journal and repository method using `FOR UPDATE SKIP LOCKED` for future worker execution.
