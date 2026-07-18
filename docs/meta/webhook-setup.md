# Webhook setup

Configure the public webhook URL at `/api/v1/integrations/instagram/webhook`. Subscribe to `messages` and `messaging_postbacks`. Verification uses `META_WEBHOOK_VERIFY_TOKEN`; POST signature validation uses `META_APP_SECRET` and `X-Hub-Signature-256`.
