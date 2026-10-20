# Instagram: Render → Raspberry, 2026-10-20

## Confirmed cause and applied OAuth correction

The live Raspberry environment retained META_OAUTH_REDIRECT_URI from Render. Instagram consequently sent the browser to the old Render service after login, although ordinary Sellora API traffic already used Raspberry.

The existing Sellora Meta application (Facebook app1061646866376512, Instagram app1575856504325341) now has exactly this OAuth redirect URI registered:

https://btc-radar.tail7f9b04.ts.net/api/v1/integrations/instagram/oauth/callback

The same URI was applied to the private Raspberry environment, with a mode0600 backup, and the Sellora container was recreated using the existing verified image37a20fd3d848406d92a71505c26995fe0edd937d. The frontend return remains:

https://sellora-web-staging.vercel.app/settings/integrations/instagram/callback

Compose now explicitly supplies these public URLs, so importing a stale Render environment cannot silently restore the old callback. Optional SELLORA_META_OAUTH_REDIRECT_URI and SELLORA_META_OAUTH_FRONTEND_CALLBACK_URL selectors support a future reviewed domain change.

## Repository changes

- The existing deployment workflow is now manual Raspberry/API/browser/OAuth verification. Its Render deploy/export jobs and push-to-main trigger are removed.
- A bounded one-time job disables native Render autodeploy for only srv-d8g092m7r5hc73aitgng after verifying service identity. It does not suspend/delete the service.
- Active staging checks use Raspberry and explicit /sellora-health. The separate NEXUS /health route is preserved.
- Mobile audit builds use the same-origin API rewrite and Raspberry server upstream.
- Provider history-sync workflows are manual, so merging their URL changes cannot trigger provider writes.
- The OAuth canary creates one short-lived OAuth state for an existing OWNER membership; it checks the generated provider URL and public invalid-state callback without exchanging a code or modifying an existing connection.

## Pending provider cutover

The Meta webhook callback still points to Render. Changing it to https://btc-radar.tail7f9b04.ts.net/api/v1/integrations/instagram/webhook requires re-entering the existing Raspberry verify token into the existing Meta application. The save has not been performed: automatic approval review required explicit consent for this secret transfer. No token was rotated or included in source, logs or screenshots.

Do not suspend Render or enable the Raspberry webhook worker before the new Meta webhook challenge succeeds. Then stop the old worker/service, verify it is suspended, enable one Raspberry worker, and verify a provider event without customer sends or fabricated Purchase events. Raspberry send/auto-send/AI flags remain disabled.

Full Instagram account authorization, successful token exchange and an incoming provider event are not established by ordinary Sellora login or by the invalid-state callback check.

## Rollback

Restore only the previous OAuth URI from the private environment backup and Meta registration if rollback is required. Keep the current database, tokens, signing/encryption keys, storage and immutable images. Never run two webhook workers during the ownership change. The frontend and backend application code do not require a rebuild for this configuration correction.
