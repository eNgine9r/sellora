# api-endpoint-inventory.md

## Sprint 9 AI and Direct endpoints

- `GET /api/v1/direct/conversations`
- `POST /api/v1/direct/conversations`
- `GET /api/v1/direct/conversations/{conversation_id}`
- `GET /api/v1/direct/conversations/{conversation_id}/messages`
- `POST /api/v1/direct/conversations/{conversation_id}/messages`
- `POST /api/v1/direct/conversations/{conversation_id}/analyze`
- `GET /api/v1/direct/conversations/{conversation_id}/analyses`
- `GET /api/v1/direct/conversations/{conversation_id}/suggestions`
- `GET /api/v1/ai/health`
- `GET /api/v1/ai/settings`
- `PATCH /api/v1/ai/settings`
- `GET /api/v1/ai/usage/summary`
- `GET /api/v1/ai/usage/events`

## Sprint 10 Instagram messaging endpoints

- `POST /api/v1/integrations/instagram/connect`
- `GET /api/v1/integrations/instagram/oauth/callback`
- `GET /api/v1/integrations/instagram/status`
- `POST /api/v1/integrations/instagram/validate`
- `POST /api/v1/integrations/instagram/disconnect`
- `GET /api/v1/integrations/instagram/webhook`
- `POST /api/v1/integrations/instagram/webhook`
- `DELETE /api/v1/integrations/instagram/data`
- `POST /api/v1/direct/conversations/{conversation_id}/reply/prepare`
- `POST /api/v1/direct/conversations/{conversation_id}/reply/send`

## 2026-10-20 integration onboarding reconciliation

Exact backend inventory: 231 routes, 130 mutation routes. Primary classifications: PUBLIC 5, COOKIE_SESSION 3, AUTHENTICATED_GLOBAL 6, WORKSPACE_SCOPED 201, FEATURE_GATED 16, INTERNAL_OR_DOCUMENTATION 0.

Added Nova Poshta reads (both authenticated workspace OWNER):
- GET /api/v1/integrations/nova-poshta/senders
- GET /api/v1/integrations/nova-poshta/sender-contacts

Meta Ads live APIs:
- POST /api/v1/integrations/meta-ads/oauth/start — workspace OWNER; one-use durable state.
- POST /api/v1/integrations/meta-ads/oauth/callback — workspace OWNER; the only code-exchange/connection-completion route.
- GET /api/v1/integrations/meta-ads/oauth/callback — explicit public, feature-gated forwarding-only boundary. Cannot consume state, exchange a code, select an account, or connect. Fixed configured redirect target; no-store/no-referrer; query redacted from Uvicorn access logs.
- GET /api/v1/integrations/meta-ads/accounts — workspace OWNER; provider-granted identifiers for explicit selection.
- POST /api/v1/integrations/meta-ads/account — workspace OWNER; revalidates provider grant and currency.
- POST /api/v1/integrations/meta-ads/sync — workspace OWNER; bounded manual read-only provider sync.
- POST /api/v1/integrations/meta-ads/disconnect — workspace OWNER; local Ads credential only.

The public callback stays classified FEATURE_GATED in the existing primary taxonomy; PUBLIC_OAUTH_FORWARD_ENDPOINTS explicitly declares its method/path exception. Exact inventory tests verify every other listed live operation retains OWNER and workspace dependencies.
