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
