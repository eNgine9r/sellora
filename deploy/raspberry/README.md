# Sellora backend on Raspberry Pi

This backend-only deployment keeps the Vercel frontend and existing Supabase PostgreSQL database. It does not modify Render deployment files, database schema, Meta callbacks, campaign settings, or customer messages. Target: btc-radar, Linux ARM64.

## Requirements and boundaries

- Docker Engine and Compose 2.30+ on the target host.
- Confirm ARM64, disk space, memory, existing ports and services before deployment.
- One API process, capped at 1 CPU, 768 MiB RAM and 128 PIDs.
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
7. Update Vercel's NEXT_PUBLIC_API_BASE_URL and rebuild the frontend. Update the matching Meta OAuth redirect/webhook URLs when the backend URL changes; verify the challenge and subscriptions with the existing app.
8. Verify one authorized canary: incoming event, one stored message, one history entry, and no duplicate processing. Do not send a customer message or fabricate a purchase to test.
9. Observe queue errors, authentication, database connectivity, resources and Direct behavior before retiring Render.

Restoring manual sends or AI behavior is a separately reviewed change. Advertising sync and Conversions API are outside this migration.

## Rollback

Disable the Raspberry worker first. Restore the previous Vercel API URL and Meta callbacks, verify routing, then resume the previous Render worker. Keep only one worker owner active. Preserve the Raspberry storage volume and pending jobs; do not run compose down -v, drop tables, delete tokens, or downgrade the shared database.

This package prepares deployment. Target-host installation, private environment transfer, backup recovery, HTTPS/OAuth validation and cutover must each have recorded evidence before migration can be called complete.
