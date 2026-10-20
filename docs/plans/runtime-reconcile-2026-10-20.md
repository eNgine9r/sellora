# Sellora production reconciliation and Issue #266

## Audited starting state

- PR #265 head: d6467bec69d95951ffe84bcae0edec066af1cd20, draft.
- All seven jobs succeeded in CI run 39466816873.
- Active Raspberry image: sellora-backend:instagram-validation-hotfix-20261020.
- Actual image ID: sha256:086f4ea10d77420c4fd82eda68546d2bf98b1bbd2c3169a6eda9d8a94e50eff1.
- Image /health reports 37a20fd3d848406d92a71505c26995fe0edd937d; this predates layered hotfixes and is not an accurate code identity.
- Live DB read-only audit confirms Alembic 202610200038. No production migration/stamp/downgrade executed.
- Cookie sessions and login throttling enabled; legacy bearer login disabled; send, auto-send and AI disabled.
- Current live frontend alias resolves to Vercel dpl_C8hiG9g6EUPJFuYXPLRgDRhhDHSy, source d05ab943d534806c1f5437afac30d0ce9d828bac on maintenance/2026-10-20-cookie-only-browser.

## Source reconciliation

Recovered source from the exact running container into a separate evidence snapshot with a SHA-256 file manifest, then integrated only missing runtime changes into an isolated branch based on #265. Preserved PR lead additions. Missing backend files include login throttle, revocable session service/routes, session-bound JWT checks, CORS allowlist, redacted SQL parameters, history field fallback and long-message-ID handling, and revisions 037/038. Role revokes in recovered migrations are guarded for plain PostgreSQL; table definitions, RLS and forward-only downgrade guards are retained.

The frontend security branch must be merged before a frontend release. Its cookie-only browser and response hardening must survive; do not deploy the original #265 frontend over it.

## Incident evidence and limits

Historical logs contain no application stack trace during the hang. Current DB activity does not show pool exhaustion or blocking. Historical trigger remains unresolved.

An isolated regression reproduces an architectural failure: synchronous DB/socket work inside the history and extraction async services blocks the only Uvicorn event loop (0.400 s induced stall produced 0.400 s loop delay). Both regression tests failed before the fix and passed after moving the entire session/async-service lifecycle into a worker thread. This mechanism is verified; it does not establish the historical trigger.

PostgreSQL connect/socket, statement and lock waits plus SQLAlchemy pool waits are now bounded. Health endpoints run asynchronously, without a DB or thread-pool dependency. Worker phase, duration, safe error class and event-loop lag expose stalls without messages, identities or credentials.

## QA findings

- Fixed actual runtime history subclass bypassing lead automation; both importer paths use one safe helper.
- Fixed explicit /leads/{id}/convert duplicating an already linked Direct prospect; reuse it under participant/conversation/lead locks.
- Fixed repeat opportunity state/action while retaining the prior order until a new order succeeds.
- PostgreSQL confirms the existing unique participant index rejects duplicate active Direct threads. A proposed sibling-thread query concern cannot occur under the actual schema; no speculative repository change was made.
- Real PG concurrency gate confirms two competing ensure calls create one Lead.
- HTTP role/tenant tests use synthetic session-bound JWTs; never live credentials.
- Security PG tests verify cookie rotation, short concurrency retry, replay revocation, revoked access rejection, normalized HMAC throttle, RLS, revision head and refusal to drop live session controls.

## Release gates

No release is authorized by a green unit test alone. Required: reconciled frontend, complete CI, isolated image/startup/migration/rollback rehearsal, synthetic browser and controlled Direct/order tests, matching live schema and exact rollback image. Production diagnostics remain read-only. No customer sends, real TTN, token changes or removal of working data.

Rollback restores the exact saved image and prior frontend deployment while retaining schema 038, private environment and storage. Never downgrade security migrations or restore an old 036-only image.
