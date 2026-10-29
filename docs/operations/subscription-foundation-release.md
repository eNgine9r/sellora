# S8.1 subscription foundation — Raspberry release overlay

This is a migration and verification overlay for the existing Raspberry release
path. It does not deploy, create subscriptions, activate billing or enforce plans.
The first rollout expects existing workspaces to remain `UNMANAGED`.

## Existing release path and prerequisites

The prior guarded handoff is
[`deploy/raspberry/sellora_s2_identity_release.py` at `ca8f740`](https://github.com/eNgine9r/sellora/blob/ca8f740c12d7a567273024141e91127d0906529c/deploy/raspberry/sellora_s2_identity_release.py)
on branch `codex/s2-identity-release-handoff`. It is not in this branch. It locks the
watchdog configuration, verifies the current image, environment and candidate
source revision, recreates only `backend` with `--pull never`, checks container
health plus `/health/ready`, updates the watchdog, and attempts to restore both
configuration files and the old image if cutover fails. Reuse that guarded sequence.

**Do not execute the historical S2 helper unchanged for S8.1.** Its old/new image
tags, immutable IDs and source revision are specific to S2. It has no database
backup or migration gate. An operator must first verify the actual runtime and
review the S8.1 pins in that existing handoff; an offline host is a release blocker.

Its recorded deployment coordinates need runtime revalidation:

| Item | Existing path/value |
| --- | --- |
| Compose project | `sellora-rpi` |
| Compose directory | `/home/btcradar/commander-workspaces/sellora-migration/repo/deploy/raspberry` |
| Compose files | `compose.yaml` and `no-memcg.yaml` in that directory |
| Deployment environment | `/home/btcradar/.config/sellora/deployment.env` |
| Watchdog state | `/home/btcradar/.local/state/sellora/api-watchdog.json` |
| Backend container | `sellora-rpi-backend-1` |
| Local readiness | `http://127.0.0.1:18000/health/ready` |

Never print the deployment environment, rendered Compose environment, token values
or Docker inspect environment. Retain the helper's environment-drift check and its
removal of inherited `SELLORA_*` / `COMPOSE_*` overrides from Compose subprocesses.

Before any live schema or image change, record passing required CI, the reviewed
commit, candidate ARM64 image ID/source label, immutable previous image, encrypted
backup and successful restore verification. Verify exactly one Meta webhook worker
and preserve provider write gates. The app's database role must have both table
permission and an appropriate RLS access path: migration 051 enables RLS with no
policies, so a non-owner role's bare `SELECT` grant is insufficient. Resolve that
role-specific deployment prerequisite before cutover; this overlay adds no grants.

Rehearse the exact previous image and startup command against schema 051 in a
disposable environment. An additive table alone does not prove image rollback:
`render-start.sh` in an old image may fail when Alembic cannot locate revision 051.
The actual Raspberry startup override must be inspected after runtime access
returns. Do not repin or execute the historical handoff before those facts exist.

## Migration gate

First reuse `.github/workflows/ci.yml`'s disposable subscription database gate:
create only `sellora_subscriptions_canary_isolated`, upgrade its full Alembic chain,
then run `SELLORA_SUBSCRIPTIONS_DISPOSABLE_CANARY=YES python -m pytest -q
tests/subscriptions`. Those tests write synthetic rows and must never run against
the live database. Include an isolated PostgreSQL 17 run when matching the
Raspberry database version. Confirm empty-table downgrade/re-upgrade in the
disposable database and populated-table downgrade refusal.

Also prove that a persisted synthetic managed term is visible through the backend
under the actual application database role in that disposable environment. An
`UNMANAGED` response alone cannot distinguish an absent row from an RLS-hidden row.
The default disposable tests using the table owner do not prove a separate runtime
role's access. Never seed a production subscription to perform this check.

Inside the pinned candidate's backend directory, with the release runner supplying
the intended database environment privately, the migration commands are:

```sh
EXPECTED_ALEMBIC_REVISION=202610290051 python scripts/verify_alembic_revision.py
python -m alembic heads
python -m alembic current
python -m alembic upgrade 202610290051
python -m alembic current
```

Gate the live upgrade on packaged head `202610290051`, live predecessor
`202610280050`, the backup/restore evidence and successful disposable canary. Stop
on a different live revision or migration error. Revision 051 has a five-second
lock timeout, creates only the new table, and performs no enrollment/backfill.
The repository's `render-start.sh` upgrades to `head` automatically; ensure the
pinned image has exactly the reviewed head before allowing startup. Do not use the
legacy Render workflow or development `docker-compose.yml` for Raspberry cutover.

## Read-only endpoint canary

`backend/scripts/verify_subscription_status.py` uses only Python's standard
library. It sends at most six GET requests to the fixed subscription endpoint,
refuses redirects and URL credentials/query strings, accepts HTTPS or loopback
HTTP, and logs only check names and result codes. It never logs server response
bodies or exception text. Supply existing, valid session-bound access tokens through
the environment using the operator's private credential mechanism; the probe does
not log in or create sessions.

| Environment variable | Meaning |
| --- | --- |
| `SELLORA_CANARY_API_URL` | Origin or `/api/v1` base, without credentials/query/fragment |
| `SELLORA_CANARY_WORKSPACE_ID` | Selected existing workspace |
| `SELLORA_CANARY_OWNER_TOKEN` | Active OWNER in the selected workspace |
| `SELLORA_CANARY_MANAGER_TOKEN` | Active MANAGER in the same workspace |
| `SELLORA_CANARY_ANALYST_TOKEN` | Active ANALYST in the same workspace |
| `SELLORA_CANARY_FOREIGN_WORKSPACE_ID` | Existing different workspace with no active membership for that owner |

From the repository root, after the guarded cutover and healthy readiness:

```sh
python backend/scripts/verify_subscription_status.py --expected-status UNMANAGED --require-denials
```

Or inside the backend image, use `python scripts/verify_subscription_status.py`
with the same flags and privately supplied canary environment. Do not put tokens
in command arguments or URLs, enable shell tracing, or copy them into reports.

A complete pass verifies the response contract: matching workspace, `UNMANAGED`, no enrollment fields,
`has_current_term=false`, `enforcement_enabled=false`, `Cache-Control: no-store`,
anonymous 401, missing-workspace 400, MANAGER/ANALYST 403 and foreign-workspace 403.
The disposable app-role visibility test remains a separate mandatory prerequisite.
Without `--require-denials`, absent optional credentials are explicitly listed in
`skipped`; that partial probe does not close the full release gate. For a future
legitimate managed term, pass its approved expected display status explicitly.

Record only image/source identity, schema revision and sanitized probe result.
If readiness or the canary fails, use the existing guarded image/config rollback
only with the startup compatibility already proven above. Retain the additive
table at 051 for that rehearsed application rollback. Do not automatically
downgrade schema. A populated table deliberately blocks downgrade and requires a
separate data-preserving review.
