# Sellora sign-in and registration

The public entry points are `/login` and `/register`. An existing account can connect Google or Facebook at `/settings/sign-in`. The first shop is created through the existing onboarding after registration. Team memberships stay with the existing Sellora user and workspace. Social sessions cannot satisfy the Platform Admin password-session requirement.

## Configure staging

1. Apply Alembic revision `202611130060` through the regular backend deployment and keep `SELLORA_AUTH_REGISTRATION_ENABLED=false` while checking the setup.
2. Use a same-origin frontend proxy for `/api/v1`. Set `SELLORA_AUTH_PUBLIC_ORIGIN` to the exact frontend origin and add that origin to `SELLORA_CORS_ALLOWED_ORIGINS`. Enable `SELLORA_COOKIE_SESSIONS_ENABLED` on the backend and `NEXT_PUBLIC_COOKIE_SESSION_AUTH_ENABLED` in the frontend build. A non-placeholder JWT secret with the configured HMAC algorithm's minimum length is required.
3. In Google Auth Platform, configure a Web application OAuth client and register `<origin>/api/v1/auth/session/access/google/callback` as the authorized redirect URI. Set `SELLORA_AUTH_GOOGLE_CLIENT_ID` and `SELLORA_AUTH_GOOGLE_CLIENT_SECRET` on the backend. The browser receives only the public client ID as part of Google's authorization URL.
4. In Meta, configure Facebook Login for the web and register `<origin>/api/v1/auth/session/access/facebook/callback` under Valid OAuth Redirect URIs. Set `SELLORA_AUTH_FACEBOOK_APP_ID` and `SELLORA_AUTH_FACEBOOK_APP_SECRET` on the backend. Test with app-role accounts and enable the required Meta access for the intended audience before public rollout. Login requests only `public_profile`.
5. Set `SELLORA_AUTH_SMTP_HOST`, `SELLORA_AUTH_SMTP_PORT`, `SELLORA_AUTH_SMTP_FROM`, and the paired `SELLORA_AUTH_SMTP_USER` and `SELLORA_AUTH_SMTP_PASSWORD` if required by the mail relay. Delivery uses implicit TLS. Email registration and Facebook registration require this service. Google registration uses an authoritative verified Google address or a Sellora email code.
6. Verify the configured provider buttons and connect a provider to an existing staging account. Sign out and back in with it, confirming the same user ID and memberships. Enable registration on staging and repeat with a fresh address and a new test shop. Confirm the provider callbacks, mail delivery, cancel, expiry and duplicate-account handling before enabling registration on the public origin.

Use separate OAuth clients or apps for staging and production. Review proxy and hosting logs to ensure authorization callback queries are excluded. The application strips callback queries from Uvicorn access logs and does not store third-party tokens.

## Rollback

Disable new registrations through `SELLORA_AUTH_REGISTRATION_ENABLED`. Keep already-linked providers configured so users can still sign in. To retire a provider, first arrange an alternative sign-in method for affected users. Preserve the migration while registered identities exist.
