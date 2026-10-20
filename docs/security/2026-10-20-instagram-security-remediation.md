# Sellora staging security hardening — 2026-10-20

## Scope and state

This document records a controlled security intervention on the **staging** system for
Instagram Direct. The operator approved remediation after the audit.

### Confirmed pre-fix vulnerability

Supabase `public.meta_webhook_events` had an `ALL` RLS policy permitting rows where
`workspace_id IS NULL`; the Supabase `anon` and `authenticated` roles also held
table-level privileges. A read-only impersonation using `SET LOCAL ROLE anon`
confirmed a row with a provider JSON payload was visible. A non-content
Supabase REST probe using a *public* publishable key returned status 206 with
count 1. No message body was retrieved.

### Applied migration

Supabase migration `lock_down_public_meta_webhook_payloads_20261020` was
successfully applied to the **staging Supabase project**:

```sql
REVOKE ALL PRIVILEGES ON TABLE public.meta_webhook_events FROM anon, authenticated;

ALTER POLICY meta_webhook_events_workspace_isolation
ON public.meta_webhook_events
USING (
  workspace_id IS NOT NULL AND
  workspace_id::text = current_setting('app.current_workspace_id', true)
)
WITH CHECK (
  workspace_id IS NOT NULL AND
  workspace_id::text = current_setting('app.current_workspace_id', true)
);
```

A precondition verified the original policy before applying changes. The actual
migration is already registered in the Supabase migration history; do **not**
automatically run this SQL a second time.

After the migration: neither `anon` nor `authenticated` has table grants, the
RLS predicate excludes `NULL` workspace IDs, and the same public REST
count request returns HTTP 401. This closes the confirmed public Data API access.

Backend behavior and signed provider delivery still require a fresh end-to-end
canary once the Raspberry Pi is back online. A privilege-checking connection
used by the backend bypasses RLS; do not assume the Data API roles are the
roles used by the application process without checking.

### Recovery SQL — manual, ONLY if explicitly approved

If a demonstrated critical regression requires immediate reversal, first
restore the previous policy and grants based on the audited prior state:

```sql
ALTER POLICY meta_webhook_events_workspace_isolation
ON public.meta_webhook_events
USING (
  workspace_id IS NULL OR
  workspace_id::text = current_setting('app.current_workspace_id', true)
)
WITH CHECK (
  workspace_id IS NULL OR
  workspace_id::text = current_setting('app.current_workspace_id', true)
);
GRANT ALL PRIVILEGES ON TABLE public.meta_webhook_events TO anon, authenticated;
```

**Security warning:** this recovery SQL reintroduces the previously confirmed
anonymous leak. It is an emergency rollback reference only, not an approved
steady-state configuration.

### CORS source fix

`backend/app/main.py` replaces wildcard origins with a validated allowlist:
`https://sellora-web-staging.vercel.app` by default in production. Optional
`SELLORA_CORS_ALLOWED_ORIGINS` accepts comma-separated *exact HTTPS origins*;
localhost HTTP is included only for non-production development. Validation
fails closed for wildcard, credentials, paths, or non-HTTPS production values.

The Raspberry backend deployed before this change is built from an immutable
image with a narrow Instagram history patch layered on top. **Do not deploy
the entire GitHub feature branch to that Pi.** Build a second narrow overlay
containing only `app/main.py`, run a no-worker canary, and preserve the
previous image selector/compose config for rollback. Keep sending disabled.

### Additional findings still open

- JWT access and refresh tokens are stored in browser `localStorage`; a
  full HttpOnly/SameSite cookie session migration requires coordinated
  front/back-end design and CSRF testing.
- API login/refresh routes require provider-independent brute-force limits
  and session revocation design before broad production rollout.
- No strict frontend CSP is configured; existing inline theme initialization
  must be moved to a nonce/hash-safe design before enabling CSP enforcement.
- Passwordless/public data API exposure has been mitigated for webhook events,
  but review all Supabase grants, functions and security-definer RPCs before
  enabling other public API features.
- Owner permissions in Your Jewelry should be reviewed interactively with
  the actual account owner; do not automatically deactivate people.
- Meta App Review, access level, backup recovery, and token revocation
  coverage require separate checks.

### Current safety gates

Keep Meta auto-send, auto-analysis and proactive customer extraction disabled.
Recheck `/health`, provider-signed inbound delivery, existing conversation
count, API CORS allow/deny preflights, and the selected frontend alias after
each deployment. Never report successful deployment without those checks.
