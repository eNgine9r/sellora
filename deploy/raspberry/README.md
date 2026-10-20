# Sellora backend on Raspberry Pi

The backend runs on btc-radar, Linux ARM64, with the existing Vercel frontend and Supabase PostgreSQL database. The Oct20 OAuth cutover replaces the inherited Render redirect configuration and removes automatic Render deployment. Database schema, stored integration tokens, encryption keys and customer messages are preserved. OAuth redirect registration and webhook/worker ownership are separate gates; see the current cutover record below.

## Recorded verification

Historical foundation evidence is in [verification-2026-10-19.json](verification-2026-10-19.json) and [target-verification-2026-10-19.json](target-verification-2026-10-19.json). The modernization release is recorded separately in [modernization-verification-2026-10-20.json](modernization-verification-2026-10-20.json), including immutable frontend/backend sources, exact CI runs, public canaries, rollback and remaining provider gates. Build-host evidence and target-host observations are labelled separately; source-equivalent frontend-only/test/documentation commits do not require rebuilding an unchanged backend.

## Requirements and boundaries

- Docker Engine and Compose 2.30+ on the target host.
- Confirm ARM64, disk space, memory, existing ports and services before deployment.
- One API process with 1 CPU and 128 PID cgroup limits. The standard Compose file requests a 768 MiB memory cgroup limit; btc-radar requires the documented no-memcg override, which limits virtual address space rather than resident memory.
- Bind the API to loopback port 18000. A separately verified HTTPS reverse proxy is required for Vercel, OAuth and Meta webhooks.
- Public ingress is not created by this package. Preserve authentication and route only Sellora traffic; do not replace existing NEXUS/BTC Radar routing.
- No local PostgreSQL, frontend, pgAdmin, Redis or unrelated service is started.
- No automatic Alembic upgrade, admin seeding, database downgrade or credential rotation.
- Preview mode disables the Instagram worker, outbound sends and AI activity. Auto-replies remain disabled.

## Preserve data and credentials first

Record the deployed Render commit, current Alembic revision and worker/send flags without displaying secrets. Verify a recoverable Supabase backup before any separately reviewed schema upgrade.

Privately copy the existing backend environment to an absolute path outside the checkout, with mode 0600. Preserve DATABASE_URL, SECRET_KEY, JWT_SECRET, META_TOKEN_ENCRYPTION_KEY and its version, provider configuration, storage configuration, API version and existing integration credentials exactly. Replacing encryption keys would make previously stored integration tokens unreadable. Do not paste secrets into terminal commands, logs, Git, PRs, or screenshots.

The private file uses raw KEY=value entries. Compose does not interpolate dollar signs or remove surrounding quotes in raw mode; copy the actual values without adding shell quoting. Do not source this file as a shell script.

The startup preflight requires non-placeholder signing keys of at least 32 characters, a PostgreSQL URL, and an image release revision. It checks the database revision in a read-only transaction. Missing, outdated or divergent database revisions block startup; they never trigger an upgrade.

Inventory all local imports and attachments on the old backend. If they live on disk, back them up and restore them into the new storage volume before cutover, preserving ownership for UID/GID 10001. If Supabase Storage is configured, retain the same bucket and credentials and verify an existing file. Copying only the database does not copy local files.

## Build an immutable ARM64 release

Use a clean, committed checkout and retain the full image ID/digest for rollback. Build on an ARM64 builder or a separately approved cross-builder:

    git diff --exit-code
    git diff --cached --exit-code
    SELLORA_REVISION=$(git rev-parse HEAD)
    docker build --platform linux/arm64 --build-arg SELLORA_REVISION="$SELLORA_REVISION" -f backend/Dockerfile.raspberry -t "sellora-backend:$SELLORA_REVISION" backend

The runtime commit is read from a file baked into the image, so a copied Render runtime variable cannot misidentify the release. The base Python image is pinned by digest. Application dependencies retain the existing repository requirements policy. Transfer the verified image privately to the target, or pull it from an already authorized private registry.

## Repeat the isolated release check

With the already built image available locally:

    python3 deploy/raspberry/smoke_test.py --image "sellora-backend:<verified-commit>" --expected-revision "<verified-commit>"

This check creates its own PostgreSQL 16 container, private synthetic credentials, temporary volume and a dedicated Docker network. It never accepts a live DATABASE_URL or uses the private production env file. It verifies that an empty database blocks startup without creating tables, explicitly upgrades only its disposable database, then checks the actual Compose deployment, release identity, disabled worker, authenticated-route protection, storage ownership and resource limits. All test containers, volumes and temporary files are removed on exit. Docker Engine, Compose 2.30+, Python 3 and a cached/pullable postgres:16-alpine image are required. The test publishes a temporary loopback port only.

## Preview without changing the current backend

Set only deployment selectors in the shell; the secret file is never printed:

    export SELLORA_IMAGE="sellora-backend:<verified-commit>"
    export SELLORA_ENV_FILE="<absolute-private-env-path>"
    export SELLORA_WORKER_ENABLED=false
    export SELLORA_SEND_ENABLED=false
    docker compose -f deploy/raspberry/compose.yaml config --quiet
    docker compose -f deploy/raspberry/compose.yaml up -d --wait backend

Do not run an unredacted compose config, docker inspect, env, or verbose connection diagnostics with live credentials.

Verify:

- Image architecture is arm64 and its revision matches the intended commit.
- Container becomes healthy; /health is a liveness check, not proof of a complete migration.
- Startup preflight passed against the expected database revision.
- /docs and /api/v1/openapi.json load locally.
- Anonymous protected endpoints still reject requests.
- Login, token refresh, workspace isolation, Direct history and existing attachments work with authorized test accounts.
- Resource consumption remains within the host budget.
- A separately configured HTTPS endpoint reaches this container and retains TLS validation.

## Controlled cutover

1. Confirm the running Render commit/schema are compatible with the new image. Stop on an unknown or mismatched live revision.
2. Preserve the old image, environment, frontend API URL, Meta callback URLs and storage snapshot.
3. Finish local and HTTPS preview checks while Render remains the active backend.
4. Stop the old Instagram worker before enabling it on Raspberry. Preserve pending webhook jobs in the shared database.
5. Set SELLORA_WORKER_ENABLED to the previously approved worker state. Keep SELLORA_SEND_ENABLED=false during the migration. Auto-sends and AI activity stay off.
6. Recreate only the Sellora backend and verify worker state through /health.
7. Set Vercel's server-side SELLORA_API_UPSTREAM_URL to the backend API base and rebuild the frontend. The legacy absolute NEXT_PUBLIC_API_BASE_URL is accepted as a server-side fallback; browser requests use same-origin /api/v1 through the Next.js rewrite. Update the matching Meta OAuth redirect/webhook URLs when the backend URL changes; verify the challenge and subscriptions with the existing app.
8. Verify one authorized canary: incoming event, one stored message, one history entry, and no duplicate processing. Do not send a customer message or fabricate a purchase to test.
9. Observe queue errors, authentication, database connectivity, resources and Direct behavior before retiring Render.

Restoring manual sends or AI behavior is a separately reviewed change. Advertising sync and Conversions API are outside this migration.

## Rollback

Disable the Raspberry worker first. Restore the previous Vercel deployment/upstream and Meta callbacks, verify routing, then resume the previous Render worker. Keep only one worker owner active. Preserve the Raspberry storage volume and pending jobs; do not run compose down -v, drop tables, delete tokens, or downgrade the shared database.

Target-host installation, preserved private environment, HTTPS API access and the same-origin frontend proxy have recorded evidence. Meta callback/redirect registration, old-worker retirement, a single active worker, a live incoming provider event and existing remote attachment reads remain separate gates; the infrastructure checks do not establish a complete live Instagram cutover.

## Verified frontend proxy

The deployed frontend uses same-origin /api/v1 requests; its server forwards them to the configured backend. API responses use Cache-Control: no-store. The external Chromium canary verified login, the current user and dashboard with direct tailnet/localhost requests blocked (Actions run 39306467890). The authenticated read-only API canary also passed through the Vercel proxy (Actions run 39312335737). These checks establish browser/API access; they do not establish Meta callback delivery, old-worker retirement, existing attachment access or a completed live Instagram cutover.

## Hosts without a memory cgroup

Check Docker MemoryLimit support before startup. On btc-radar the existing boot configuration disables the memory controller. The optional no-memcg.yaml override bounds the single API process address space to 768 MiB using the kernel RLIMIT_AS resource limit. CPU and PID cgroup limits remain in effect. This does not provide a container-wide resident-memory limit. Do not claim otherwise or reboot unrelated services as part of this fallback. Add the override as a second Compose file and verify /proc/1/limits and actual API operation.

The fallback also sets MALLOC_ARENA_MAX=2. On ARM64 the default glibc arenas reserved enough virtual address space to reach RLIMIT_AS while resident memory remained around 170 MiB, preventing the API from creating worker threads. Bounding the allocator arenas preserves the address-space guard and leaves room for the application's existing thread pool. Verify actual public login and read requests after applying this override.

## Modernization release2026-10-20

Frontend 71bcfd0 is READY at the existing public alias; backend 37a20fd is running on btc-radar. The backend tree is identical across these commits. Exact source, image, deployment IDs and current read-only auth/API/browser canaries are recorded in modernization-verification-2026-10-20.json. The existing NEXUS /health route still returns200; Sellora health remains /sellora-health. Resource and private-environment observations from installation remain dated deployment evidence: the Pi management channel was offline during the Oct20 recheck, while public auth/read canaries passed.

For a feature rollback, retain frontend dpl_zEUi5VR5fdwmtjNjj2bgEY7NaPER/a1a5d5a and backend image sellora-backend:8c2a9b2c83056a8f8719c5b06ddedb6c65314fb4. Restore only the intended immutable release/selector, preserve the private environment and storage, and keep worker/send/AI disabled. No database downgrade or Render-worker resumption is required for this modernization rollback. A provider ownership/callback cutover remains a separate operation. See the delivery record in docs/plans/sellora-modernization-delivery-2026-10-20.md for functional outcomes and remaining gates.

## Instagram OAuth cutover2026-10-20

The inherited Render redirect was corrected on the live Pi and in the existing Meta application. Compose pins the Raspberry OAuth redirect and Vercel frontend return independently of the copied private environment. The previous Render deployment workflow now offers manual verification and a bounded native-autodeploy retirement operation; it cannot deploy to Render. All active workflow API destinations use Raspberry, with /sellora-health where needed.

See [the current cutover record](../../docs/plans/sellora-instagram-cutover-2026-10-20.md). The Meta webhook callback save, old-service suspension, single-worker takeover and real account authorization remain pending gates. Do not interpret the OAuth URL correction as a completed webhook cutover.
