# Sellora — Instagram Login status validation, 2026-10-20

## Context

The Render-to-Raspberry callback and webhook cutover is already in place. The
running Raspberry backend reports status=ok, Meta webhook worker enabled,
running, and processing enabled; outgoing send, auto-send, and AI auto-analysis
are disabled. Render's former health endpoint responds HTTP 503.

Two workspace-scoped connection records exist:
- Your Jewelry — CONNECTED, stored token expiry 2026-12-19 UTC.
- Sellora QA — Sprint 8A.1 — TOKEN_EXPIRED, stored expiry 2026-09-16 UTC.

A read-only provider probe on the connected store returned:
- IG Business profile: HTTP 200.
- subscribed_apps: HTTP 200, with all four required webhook fields.
- /me/permissions: HTTP 400, IGApiException code 100.

The Instagram Login path uses graph.instagram.com, unlike the Facebook Login
graph.facebook.com permission graph. The existing manual validation path
requested the unsupported /me/permissions graph even though prior OAuth
grants and the live webhook subscription were already available.

## Focused correction

- During manual revalidation, pass the stored OAuth grant snapshot to the
  profile client so it does not query the unsupported permissions endpoint.
- Still validate the current Meta account profile, professional account
  type, account identity and live webhook subscription. A stored snapshot
  by itself is NOT evidence of a currently functioning connection.
- Reject locally known expired tokens before making a network request.
- Keep workspace isolation, existing status enums, OAuth tokens, active
  provider subscriptions, and all send-related feature gates unchanged.
- Do not fabricate customer messages, Purchase events, leads, or orders.

The explicit manual validate button retains the existing service contract:
it may reassert the provider subscription and then read back confirmed fields.
This patch does not automatically invoke that mutation in production.

## Verification

- Python compilation on modified Python files: PASS.
- Focused OAuth tests: 15 passed.
- Full Meta Instagram integration tests: 69 passed.
- Patch is isolated on a feature branch. Production runtime not restarted.

## Remaining release gates

1. Review and merge stacked Raspberry deployment, UX and cutover PRs in
   dependency order after CI checks and deployment planning.
2. Deploy this validation fix after those foundations are approved.
3. Verify manual validation through authenticated OWNER session.
4. Check a real Instagram Direct message from an authorized tester against
   workspace, conversation and lead. Synthetic webhook samples are not enough.
5. Keep QA expired connection isolated. Do not disconnect the production IG
   account merely to update a QA token.
