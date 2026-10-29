# S8 schema 049 → 052: native owner handoff

The fixed helper is `deploy/raspberry/sellora_s8_subscription_release.py`, adapted
from the historical S2 handoff at `ca8f740`. Its publishable scope is a read-only
native preflight and a gated, fake-runner-tested state machine. **It is not an
accepted live rollout command.** Production remains on the original image/schema
until the missing native facts and backup proof are reviewed and pinned.

In the reviewed checkout, from an interactive terminal as the native configuration
owner (UID 1000), the regular preflight command is:

```sh
python3 deploy/raspberry/sellora_s8_subscription_release.py --preflight
```

It performs no systemctl stop/start, configuration writes, container creation or
migration. It reads only the fixed release/configuration paths, image/container
metadata, schema/role flags, loopback health endpoints and the expected service
`sellora-runtime-health-watchdog.service` and timer
`sellora-runtime-health-watchdog.timer` in the user manager. Their names and scope
come from the owner's native inspection on 29 October 2026. The old assumed
`sellora-api-watchdog.service` was not found. The service's `TriggeredBy` and timer's
`Triggers` must identify each other exactly. Output omits environment values, database URLs,
tokens and response bodies. Exit 1 with `PREFLIGHT_BLOCKED` is expected while pins
are incomplete; other failures have bounded check codes.

That inspection observed the watchdog service as `activating`, its timer as active,
and three backup timers (`sellora-db-backup`, `sellora-google-drive-backup`,
`sellora-offhost-encrypted-backup`) as active. Their services were inactive with
successful last results. These are observations, not proof of shared-lock behavior,
backup encryption, freshness or a verified restore. System `list-unit-files` failed,
so the system-manager discovery must not be described as exhaustive.

Read-only preflight collects both watchdog fragment paths/SHA-256s and the remaining
gates even when a unit is `activating`, `deactivating`, `failed`, or otherwise outside
`active`/`inactive`. It adds `watchdog_unit_stability` to `missing` and reports the
observed state. `--apply` rejects any missing gate before lifecycle operations;
its post-stop/start state checks remain strict. Unit identity, loaded state,
fragment paths and permissions still fail closed. Preflight does not wait for,
stop or otherwise alter a running watchdog.

An `unsafe_file_permissions` failure also reports a `file` object containing only
the failing path, octal mode (for example `0664`), UID and GID. It reports no file
contents or subprocess error text. The permission guard still blocks both preflight
and apply; the helper never changes file permissions.

The separate service inventory remains available for future identity/context
investigation:

```sh
python3 deploy/raspberry/sellora_s8_subscription_release.py --inspect-services
```

This separate read-only mode uses only `systemctl list-unit-files`,
`list-units --all` and `show` against both user and system managers. It includes the
fixed expected watchdog service and at most 16 discovered names per manager,
strictly filtered to `sellora*watchdog*` / `sellora*backup*` services and timers.
One JSON reports explicit scopes, names, allowlisted unit metadata and bounded
query failure codes; it excludes stderr, logs, contents, ExecStart and Environment.
Values over 2048 characters are omitted and their field names recorded. No files,
Docker, database, or unit lifecycle operations are used. Missing units/managers
remain observations, and successful collection does not approve a rollout.

Inspection cannot be combined with preflight/apply and does not alter their fixed
user-manager pins or guards. The historical S2 helper contains no systemctl
operations and establishes neither namespace. Source observations from either
mode do not fix service configuration or approve a rollout. Following the reviewed
native identity facts above, `--preflight` reports the remaining source, lock and
backup gates. Once those are the only blockers, use the source handoff below.

This command belongs in the owner's native session. A remote-control policy denied
access to the watchdog service and protected configuration writes; do not use this
helper through that tool or substitute another interface to bypass the boundary.
No sudo, system unit lifecycle operation, permission change or policy change is included.

## Unresolved facts

- Reviewed unit fragment contents and invoked source. The owner's subsequent
  native preflight collected both original unit hashes, confirmed matching fragment
  filenames, no drop-ins and `NeedDaemonReload=no`. Those original hashes bind the
  collector below, but remain observations until actual source review; the release
  helper's `UNIT_PINS` is still empty. Drop-ins or `NeedDaemonReload` block apply
  until reviewed.
- Actual shared watchdog lock/source behavior. The historical lock path remains
  unverified; `LOCK_VERIFIED` is false.
- An owner-approved encrypted backup creator and restore-verification mechanism,
  plus the private evidence location. None was found in the repository or historical
  helper. No backup/encryption/restore procedure is invented here.

The apply path remains blocked by empty `UNIT_PINS`, unset `BACKUP_EVIDENCE_FILE`,
false `BACKUP_MECHANISM_VERIFIED` and the lock-verification gate.
Native observations do not automatically promote themselves into trusted pins.
After reviewing those facts, update the fixed pins through normal code review and
rerun the fake-runner suite before considering the explicit `--apply` mode.

## Next: owner-controlled source review

The source/lock/backup gates cannot be resolved by pinning observed hashes or
successful timer results. In the reviewed checkout, the next native owner step is:

```sh
python3 deploy/raspberry/sellora_s8_source_review.py --prepare
```

This separate UID-1000/TTY-only utility reads exactly the eight known watchdog,
DB-backup, offhost-encrypted-backup and Google Drive backup service/timer files in
`/home/btcradar/.config/systemd/user`. The two watchdog original SHA-256s must match
the hashes supplied by the owner's native preflight. These checks bind collection
to those observed originals; they do not approve their behavior or populate the
release helper's `UNIT_PINS`.

Only static absolute script tokens on `ExecStart`, `ExecStartPre` and `ExecStartPost`
can add files: a `sellora`-prefixed basename directly in
`/home/btcradar/.local/bin`, ending in `.py`/`.sh` or extensionless with an explicitly
recognized text shebang. It performs no directory scan or transitive source
discovery, follows no symlinks (including ancestors), reads no binary or credential,
environment, state, log or archive files, and executes no collected source. Limits
are eight unit files at 16 KiB each, sixteen direct scripts at 128 KiB each and
512 KiB total original bytes. Missing/unsupported direct inputs are recorded as
omissions; a changed or unreadable required watchdog original fails collection.
Inline, shell or dynamic commands outside the supported direct forms remain
explicitly incomplete. Other dependencies and drop-ins remain uncollected.

It writes only one local Markdown draft at
`/home/btcradar/sellora-s8-source-review-<unique>/review.md`, directory `0700`, file
`0600`. JSON stdout contains its path, source metadata/original hashes, redaction
locations, omissions and `review_required=true`, never raw source or exception
text. No upload, source execution, service/Docker/database operation, protected
configuration update, backup production or release approval occurs.

**The owner must inspect and edit that exact draft locally before explicitly
attaching it in chat.** Unit Environment/credential directives (including
continuations), other sensitive directive values and unsupported Exec command
values are omitted. Obvious script credential assignments receive conservative
redaction; ambiguous multiline assignments omit the remainder. This is not
comprehensive sanitization: source/comments may still contain inline secrets.
Remove them before attachment and identify all manual redactions. Redactions that
affect lock, command, encryption or restore behavior leave that gate unresolved.
Original hashes identify original bytes, not edited/redacted copies.

Do not run this utility through NEXUS, auto-upload the draft, copy it into a project
path for remote reading, or read it back through another automated interface. The
owner-controlled attachment is the deliberate handoff. After actual source review,
a narrowly reviewed native producer/isolated-restore adapter can establish fresh
encrypted backup evidence. No evidence receipt or verified flag is created here.

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
