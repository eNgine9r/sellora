# S8 schema 049 → 052: native owner handoff

The fixed helper is `deploy/raspberry/sellora_s8_subscription_release.py`, adapted
from the historical S2 handoff at `ca8f740`. Its publishable scope is a read-only
native preflight and a gated, fake-runner-tested state machine. **It is not an
accepted live rollout command.** Production remains on the original image/schema
until the missing native facts and backup proof are reviewed and pinned.

In the reviewed checkout, from an interactive terminal as the native configuration
owner (UID 1000), run only this concrete discovery command:

```sh
python3 deploy/raspberry/sellora_s8_subscription_release.py --preflight
```

It performs no systemctl stop/start, configuration writes, container creation or
migration. It reads only the fixed release/configuration paths, image/container
metadata, schema/role flags, loopback health endpoints and the known user service
`sellora-api-watchdog.service`. Its `TriggeredBy` fact is reported without guessing
or querying an unverified timer. Output omits environment values, database URLs,
tokens and response bodies. Exit 1 with `PREFLIGHT_BLOCKED` is expected while pins
are incomplete; other failures have bounded check codes.

An `unsafe_file_permissions` failure also reports a `file` object containing only
the failing path, octal mode (for example `0664`), UID and GID. It reports no file
contents or subprocess error text. The permission guard still blocks both preflight
and apply; the helper never changes file permissions.

This command belongs in the owner's native session. A remote-control policy denied
access to the watchdog service and protected configuration writes; do not use this
helper through that tool or substitute another interface to bypass the boundary.
No sudo, system unit operation, permission change or policy change is included.

## Unresolved facts

- Actual timer identity, both unit fragment paths/checksums, drop-in paths and loaded
  source state. Drop-ins or `NeedDaemonReload` block apply until reviewed.
- Actual shared watchdog lock/source behavior. The historical lock path remains
  unverified; `LOCK_VERIFIED` is false.
- An owner-approved encrypted backup creator and restore-verification mechanism,
  plus the private evidence location. None was found in the repository or historical
  helper. No backup/encryption/restore procedure is invented here.

The apply path remains blocked by unset `TIMER_UNIT`, `UNIT_PINS`,
`BACKUP_EVIDENCE_FILE`, `BACKUP_MECHANISM_VERIFIED` and the lock-verification gate.
Native observations do not automatically promote themselves into trusted pins.
After reviewing those facts, update the fixed pins through normal code review and
rerun the fake-runner suite before considering the explicit `--apply` mode.

The evidence gate defines only an input receipt, not a backup producer: owner-only
JSON and an owner-only nonempty encrypted artifact whose SHA-256 matches the
receipt. Required receipt fields are `version=1`, `schema=202610270049`,
`source_image` matching the current image ID, `encrypted=true`,
`restore_verified=true`, timezone-aware `backup_completed_at` and
`restore_verified_at`, `artifact_path` and `artifact_sha256`. Backup completion must
be within one hour and restoration must follow it. Encryption/restoration remain
attestations from the separately reviewed producer; a JSON flag alone does not
establish either fact, and cannot remove the mechanism-verification gate.

## Gated transition and recovery

The image IDs are pinned in the helper. Actual Pi rehearsals verified bridge
startup at 049 and 052, candidate startup at 052, exact live Compose command with
`RLIMIT_AS=805306368`, non-root image user, matching PostgreSQL 17 non-superuser /
BYPASSRLS role, 121 subscription tests and the isolated sale canary. Those rehearsals
did not migrate or cut over production.

Once all gates are resolved, the state machine stops the verified **user** timer
and service, confirms both inactive, then holds the shared watchdog lock. It saves
private configuration snapshots, stages **both bridge pointers**, recreates and
verifies bridge049, runs one transactional Alembic upgrade to 052, then stages and
verifies the candidate. The inherited Compose environment/startup checks remain;
only `backend` is recreated, with `--pull never`.

Every caught exception or interrupt after staging attempts bridge-pointer recovery,
including after migration or a partial pointer write. Original 049-only pointers
are never restored. Schema is never downgraded. The original timer active/inactive
state is restored after pointers are verified; if pointer recovery cannot be
confirmed, the timer stays quiesced and native intervention is required. SIGINT,
SIGTERM and SIGHUP are handled; SIGKILL/power loss still require native inspection.

Readiness and a GET-only anonymous 401 probe are required. Existing valid tokens
permit the separately pinned strict subscription canary; values remain in the
environment and never enter command arguments or Compose overrides. Missing tokens
produce `authenticated_canary=MISSING` and exit 2 after a healthy apply, leaving that
gate explicitly open. No token/session is forged and no production test rows are
created. A real authenticated canary failure attempts bridge recovery.
