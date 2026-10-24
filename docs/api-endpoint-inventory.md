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

## Meta Ads live read-only connection

- OWNER: POST /api/v1/integrations/meta-ads/oauth/start
- OWNER: POST /api/v1/integrations/meta-ads/oauth/callback (state/code exchange)
- Public, feature-gated: GET /api/v1/integrations/meta-ads/oauth/callback (redirect only)
- OWNER: GET /api/v1/integrations/meta-ads/accounts
- OWNER: POST /api/v1/integrations/meta-ads/account
- OWNER: POST /api/v1/integrations/meta-ads/sync
- OWNER: POST /api/v1/integrations/meta-ads/disconnect
- Workspace-scoped status and synthetic discovery/preview retain existing gates.

The OAuth GET redirect does not exchange or disclose a token. The authenticated OWNER POST consumes durable, workspace/user-scoped state once. Daily USD/UAH conversion uses the existing manual sync endpoint; it adds no public endpoints.

Inventory reconciled to 230 routes and 133 mutation routes: 7 public routes, 6 authenticated global routes, 202 workspace routes and 15 feature-gated routes. The session login/refresh/logout endpoints are public authentication mechanisms with existing origin/session controls; upgrade and logout-all require authentication. Public classification is method-sensitive for Meta OAuth callback.
