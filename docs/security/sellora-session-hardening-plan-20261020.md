# Sellora — auth/session hardening implementation plan

**Date:** 2026-10-20  
**Status:** PROPOSED / NOT DEPLOYED  
**Priority:** High, before opening Sellora to additional sales staff  
**Environment:** Raspberry Pi API behind the Vercel same-origin `/api/v1` proxy; Instagram Direct must keep working.

## Verified existing design (source audit)

- `frontend/src/services/auth.service.ts` stores both bearer access and refresh JWTs in persistent browser `localStorage`.
- `frontend/src/stores/auth.store.tsx` restores these tokens automatically and clears local state on logout.
- `backend/app/api/v1/auth.py` returns JWT pairs directly from `POST /auth/login` and `POST /auth/refresh`.
- `backend/app/services/auth_service.py` issues **new stateless refresh JWTs on each refresh**, without session ID, token rotation state, replay detection, or a server-side revoke operation. A UI logout does not revoke any stolen refresh token.
- There is no evident application-level login rate limit in those handlers.
- Runtime uses strong non-default JWT secrets and Argon2 password hashes. Instagram Meta token storage is encrypted server-side; it is separate from the Sellora browser login tokens.

**Threat model:** Script injection/browser extension access to `localStorage`, stolen refresh token replay, brute-force password attempts, lost sales staff device, and long-lived session after staff access is revoked. These risks should be reduced without disconnecting `@breezyfyshop` or changing provider access tokens.

## Implementation order and controls

### 1. Server-side session table and refresh rotation

Add `auth_sessions` with a UUID session id, user_id, hash of a high-entropy random refresh secret, absolute expiry, rolling expiry, revoked_at, last_used_at, created_at, client_label and optional coarse audit telemetry. Refresh secrets never appear in logs or plaintext database storage. Hash with SHA-256/HMAC of high-entropy random values (not passwords). Use transaction-level concurrency control so two simultaneous refreshes do not inadvertently allow replay; define a short overlap policy or strictly fail closed with client-side single-flight logic.

- `POST /auth/session/login`: validate credentials, create a session, return a short-lived access token (memory only), set `HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth/session` refresh cookie, with bounded Max-Age.
- `POST /auth/session/refresh`: atomically rotate the session refresh secret, replace the cookie, issue a new access token; reject revoked, expired or replayed old secrets. Use Origin and CSRF checks for state-mutating cookie requests; no wildcard CORS.
- `POST /auth/session/logout`: revoke the server session, expire the refresh cookie and clear frontend in-memory tokens.
- `POST /auth/session/logout-all`: authenticated OWNER/self-service action to revoke all sessions for that user after reauthentication.
- Existing `/auth/login` and `/auth/refresh` stay temporarily available only during an explicitly bounded migration window; then retire, monitor and reject legacy refresh calls. Do not leave an indefinite weaker pathway.

For short-lived access JWTs, keep `Authorization: Bearer` sent by the frontend but hold the access token **in memory only**. On page reload call the same-origin refresh endpoint to obtain another access JWT. `localStorage` holds only non-secret display preferences and selected workspace, not access or refresh tokens.

### 2. Credential-stuffing defence

Deploy a shared limit store across all backend workers (Redis or an audited PostgreSQL implementation). Limits must use trusted proxy IP attribution (do not trust arbitrary client-submitted `X-Forwarded-For`). Apply separate thresholds for failed login per identifier and per IP, refresh endpoint, and password reset requests; return 429 with `Retry-After`. Prefer gradual backoff and manual recovery to permanent account lockout. Never log raw passwords, tokens, session secrets, or complete request bodies. Ensure the rate store cannot be bypassed simply by scaling containers/restarting the Pi.

### 3. Browser XSS and CSRF

Move the inline Next.js theme bootstrap to a CSP-compatible script flow. Start with **Content-Security-Policy-Report-Only** to collect safe failure metadata without collecting tokens/customer messages. Then enable enforced `script-src` with per-request nonce or a fully supported strict-hash setup; retain `frame-ancestors 'none'`, `object-src 'none'`, `base-uri 'self'`. Review every `dangerouslySetInnerHTML` and HTML rendering sink. Cookie-auth mutations require Origin/Referer and CSRF verification even when SameSite=Lax is configured.

### 4. Access control and audit

Use `workspace_users.is_active` on every workspace-scoped endpoint; never trust a user-supplied workspace ID without a membership check. Verify that an inactive OWNER is excluded from accessible roles. Ensure JWT access validation consults active user + membership server-side. Provide auditable active-session listing and explicit revoke controls for account owners, without showing secrets in UI.

### 5. Release, migration and rollback

1. Provision DB schema via reviewed Alembic migration with no destructive changes.
2. Add server session routes; old sessions still work during controlled pilot.
3. Add test coverage for cookie flags, CSRF, proxy header spoofing, refresh concurrency/replay, session revoke, per-role denial, and request burst throttling.
4. Test in separate QA workspace with **synthetic account data** and in an isolated Pi canary with outbound Instagram messaging disabled.
5. Switch frontend behind a feature flag only after Google Chrome desktop/mobile QA. Verify user remains signed in or receives an intentional, communicated one-time login prompt. Preserve all Direct records/orders.
6. Run a staged deprecation deadline for stateless legacy refresh; do not silently deactivate customers' sessions. Record dashboard metrics, monitor 401/429 rates and rollback safely if widespread regressions occur.
7. Keep rollback of schema additive and credentials unchanged; never roll back RLS/CORS security fixes to resurrect a confirmed exposure.

## Release acceptance gates

- [ ] No access or refresh JWT in browser `localStorage` or sessionStorage
- [ ] Refresh cookie has HttpOnly, Secure, SameSite=Lax (or stricter after validation) and narrow path
- [ ] Old refresh secret rejected after rotation; revoked session cannot refresh
- [ ] Session refresh remains correct under concurrency (no false-positive mass logout)
- [ ] Cookie-auth mutation from foreign Origin blocked
- [ ] Login burst from same attacker cannot avoid shared 429 limiter
- [ ] OWNER, MANAGER, ANALYST role permissions verified
- [ ] Normal Instagram OAuth / webhook callback still works
- [ ] Real inbound Direct and historical imports unchanged; no automatic sends
- [ ] Both Pi and Vercel can be independently rolled back with monitoring
- [ ] Owner-side iPhone signed-in browser acceptance verified

**Do not deploy the session rewrite as a single untested change.**
