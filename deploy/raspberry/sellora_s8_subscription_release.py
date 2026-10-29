#!/usr/bin/env python3
"""Fixed S8 owner-session handoff. Default preflight is read-only; --apply mutates.

Adapted from ca8f740's S2 handoff. No sudo, remote-control API, backup creator,
credential output, schema downgrade, or recovery to the original 049-only image.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

OWNER_UID = 1000
CURRENT_TAG = "sellora-backend:s2-identity-candidate-df3dcd2"
CURRENT_ID = "sha256:33be76916fd87821a3f02addb900e188047308407189a78eaa3a8c72b3d5580f"
CURRENT_SOURCE = "df3dcd29de48de0b5e1292d1087b431490e720a4"
CANDIDATE_TAG = "sellora-backend:saas-s82-candidate-d7615b7"
CANDIDATE_ID = "sha256:3284590150cbbe02e0d664d95bd9360240a2f99a1ca6298fd2868eafd8d820d4"
CANDIDATE_SOURCE = "d7615b72499ac02b6b3142f7d25f8899266ffb7c"
BRIDGE_TAG = "sellora-backend:saas-s82-bridge-d7615b7"
BRIDGE_ID = "sha256:aeb86a73fad89d7b287ded6648953c45b74f2f903435b790a6f07a24ad10cda8"
BRIDGE_SOURCE = CURRENT_SOURCE
START_SCHEMA, TARGET_SCHEMA = "202610270049", "202610290052"
ENV_FILE = Path("/home/btcradar/.config/sellora/deployment.env")
PLAN_FILE = Path("/home/btcradar/.local/state/sellora/api-watchdog.json")
LOCK_FILE = PLAN_FILE.with_suffix(".lock")
COMPOSE_DIR = Path("/home/btcradar/commander-workspaces/sellora-migration/repo/deploy/raspberry")
CONTAINER = "sellora-rpi-backend-1"
SERVICE_UNIT = "sellora-api-watchdog.service"
INSPECT_PROPERTIES = ("Id", "LoadState", "ActiveState", "FragmentPath", "TriggeredBy", "Triggers", "DropInPaths",
                      "NeedDaemonReload", "UnitFileState", "User", "Group", "Result", "ExecMainStatus", "LastTriggerUSec")
INSPECT_PATTERNS = ("sellora*watchdog*.service", "sellora*watchdog*.timer", "sellora*backup*.service", "sellora*backup*.timer")
INSPECT_UNIT_LIMIT = 16  # Discovered units per manager, plus the fixed expected service.
INSPECT_NAME = re.compile(r"sellora[A-Za-z0-9_.@:-]*(?:watchdog|backup)[A-Za-z0-9_.@:-]*\.(?:service|timer)", re.ASCII)
# Unknown runtime facts remain unset. Native preflight may observe them; it does
# not turn observations into trusted apply pins or guess a timer name/path.
TIMER_UNIT: str | None = None
UNIT_PINS: dict[str, tuple[str, str]] = {}  # unit -> (FragmentPath, SHA-256)
LOCK_VERIFIED = False
# Parent verified exact Pi images: bridge049/052, candidate052, matching PG17
# role, 121 subscription tests and isolated production-mode sale canary.
IMAGE_REHEARSALS_VERIFIED = True
BACKUP_EVIDENCE_FILE: Path | None = None
BACKUP_MECHANISM_VERIFIED = False
BACKUP_MAX_AGE_SECONDS = 3600
SCRIPT_FILE = Path(__file__).absolute()
CANARY_FILE = SCRIPT_FILE.parents[2] / "backend/scripts/verify_subscription_status.py"
CANARY_SHA256 = "ac5f1719034b0ebee65d9cf631a3fb89845b0e28164658a163d0e56f17cb4e29"
API_ORIGIN = "http://127.0.0.1:18000"
COMPOSE = ("docker", "compose", "--project-name", "sellora-rpi", "--project-directory", str(COMPOSE_DIR),
           "--env-file", str(ENV_FILE), "-f", str(COMPOSE_DIR / "compose.yaml"),
           "-f", str(COMPOSE_DIR / "no-memcg.yaml"))
DB_STATE_CODE = """import json
from sqlalchemy import text
from app.database.session import engine
with engine.connect() as c:
    heads = list(c.execute(text('SELECT version_num FROM public.alembic_version')).scalars())
    role = c.execute(text('SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user')).one()
print(json.dumps({'heads': heads, 'superuser': role[0], 'bypassrls': role[1]}))
"""


class ReleaseError(Exception):
    """Only static bounded codes may enter operator output."""


class UnsafeFilePermissions(ReleaseError):
    def __init__(self, path: Path, info: os.stat_result) -> None:
        super().__init__("unsafe_file_permissions")
        self.file_metadata = {
            "path": str(path), "mode": f"{stat.S_IMODE(info.st_mode):04o}",
            "uid": info.st_uid, "gid": info.st_gid,
        }


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ReleaseError(code)


def command(*args: str, env: dict[str, str] | None = None, timeout: int = 120) -> str:
    clean = {key: value for key, value in os.environ.items() if not key.startswith(("SELLORA_", "COMPOSE_"))}
    try:
        result = subprocess.run(args, capture_output=True, text=True, env=clean if env is None else env,
                                timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        raise ReleaseError("command_failed") from None
    require(result.returncode == 0, "command_failed")
    return result.stdout


def regular_file(path: Path, *, owner: int | None = -1, private: bool = False) -> None:
    owner = OWNER_UID if owner == -1 else owner
    require(path.is_absolute() and not any(part.is_symlink() for part in (path, *path.parents)), "symlink_or_relative_path")
    try:
        info = path.stat()
    except OSError:
        raise ReleaseError("required_file_missing") from None
    require(stat.S_ISREG(info.st_mode), "not_regular_file")
    require(owner is None or info.st_uid == owner, "file_owner_mismatch")
    if info.st_mode & (0o077 if private else 0o022):
        raise UnsafeFilePermissions(path, info)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def unit_state(name: str) -> dict[str, str]:
    require(name == SERVICE_UNIT or TIMER_UNIT is not None and name == TIMER_UNIT, "unrecognized_unit")
    raw = command("systemctl", "--user", "show", "--no-pager",
                  "--property=Id,LoadState,ActiveState,FragmentPath,TriggeredBy,DropInPaths,NeedDaemonReload", name)
    state = dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)
    require(state.get("Id") == name and state.get("LoadState") == "loaded", "unit_not_loaded_or_recognized")
    require(state.get("ActiveState") in {"active", "inactive"}, "unit_not_stable")
    fragment = Path(state.get("FragmentPath", ""))
    require(fragment.name == name, "unit_fragment_mismatch")
    regular_file(fragment, owner=None)
    state["sha256"] = digest(fragment)
    return state


def _inspect_query(scope: str, action: str, unit: str | None = None) -> tuple[str, dict]:
    require(scope in {"user", "system"}, "inspection_scope_not_allowed")
    if action == "show":
        require(isinstance(unit, str) and len(unit) <= 255 and INSPECT_NAME.fullmatch(unit) is not None, "inspection_unit_not_allowed")
        arguments = ("show", "--no-ask-password", "--no-pager", "--property=" + ",".join(INSPECT_PROPERTIES), unit)
    else:
        require(action in {"list-unit-files", "list-units"}, "inspection_query_not_allowed")
        arguments = (action, "--no-ask-password", "--no-legend", "--no-pager", "--plain", *(("--all",) if action == "list-units" else ()), *INSPECT_PATTERNS)
    clean = {key: value for key, value in os.environ.items() if not key.startswith(("SELLORA_", "COMPOSE_"))}
    try:
        result = subprocess.run(("systemctl", "--" + scope, *arguments), stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True, env=clean, timeout=5, check=False)
    except subprocess.TimeoutExpired:
        return "", {"code": "query_timeout"}
    except (OSError, subprocess.SubprocessError):
        return "", {"code": "query_unavailable"}
    return result.stdout, {"code": "ok" if result.returncode == 0 else "query_failed", "exit_code": result.returncode}


def inspect_services() -> dict:
    require(os.getuid() == OWNER_UID and os.isatty(0), "native_owner_terminal_required")
    scopes = []
    for scope in ("user", "system"):
        discovered, queries = set(), {}
        for action in ("list-unit-files", "list-units"):
            raw, query = _inspect_query(scope, action)
            queries[action] = query
            if query["code"] == "ok":
                for line in raw.splitlines():
                    parts = line.split()
                    name = parts[0] if parts else ""
                    if len(name) <= 255 and INSPECT_NAME.fullmatch(name) and name != SERVICE_UNIT:
                        discovered.add(name)
        names = sorted(discovered)[:INSPECT_UNIT_LIMIT]
        units = []
        for name in (SERVICE_UNIT, *names):
            raw, query = _inspect_query(scope, "show", name)
            fields, oversized = {}, []
            for line in raw.splitlines():
                key, separator, value = line.partition("=")
                if separator and key in INSPECT_PROPERTIES:
                    if len(value) <= 2048:
                        fields[key] = value
                    else:
                        oversized.append(key)
            units.append({"unit": name, "query": query, "fields": fields, "oversized_fields": sorted(set(oversized))})
        scopes.append({"scope": scope, "known_units": [SERVICE_UNIT], "discovered_units": names,
                       "discovery_truncated": len(discovered) > INSPECT_UNIT_LIMIT, "queries": queries, "units": units})
    return {"result": "SERVICE_INSPECTION", "diagnostic_only": True, "scopes": scopes}


def image(tag: str, expected_id: str, source: str) -> None:
    item = json.loads(command("docker", "image", "inspect", tag))[0]
    require(item.get("Id") == expected_id and item.get("Architecture") == "arm64" and item.get("Os") == "linux", "image_pin_mismatch")
    require(item.get("Config", {}).get("Labels", {}).get("org.opencontainers.image.revision") == source, "source_pin_mismatch")
    if tag in {BRIDGE_TAG, CANDIDATE_TAG}:
        require(item.get("Config", {}).get("User") == "10001:10001"
                and item.get("Config", {}).get("Cmd") == ["python", "scripts/start_raspberry.py"], "image_startup_pin_mismatch")


def container() -> dict:
    return json.loads(command("docker", "inspect", CONTAINER))[0]


def schema() -> str:
    state = json.loads(command("docker", "exec", "--workdir", "/app", CONTAINER, "python", "-c", DB_STATE_CODE, timeout=30))
    require(state.get("superuser") is False and state.get("bypassrls") is True, "database_role_drift")
    heads = state.get("heads")
    require(isinstance(heads, list) and len(heads) == 1, "database_revision_ambiguous")
    return heads[0]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_code(path: str, headers: dict[str, str] | None = None) -> int:
    try:
        with build_opener(NoRedirect()).open(Request(API_ORIGIN + path, headers=headers or {}, method="GET"), timeout=5) as response:
            return response.status
    except HTTPError as exc:
        code = exc.code
        exc.close()
        return code
    except Exception:
        return 0


def healthy(expected_id: str) -> bool:
    current = container()
    return (current.get("Image") == expected_id
            and current.get("State", {}).get("Health", {}).get("Status") == "healthy"
            and http_code("/health/live") == 200 and http_code("/health/ready") == 200)


def wait_for(expected_id: str, expected_schema: str) -> None:
    for _ in range(100):
        if healthy(expected_id):
            require(schema() == expected_schema, "unexpected_database_revision")
            return
        time.sleep(1)
    raise ReleaseError("readiness_failed")


def compose_config() -> dict:
    return json.loads(command(*COMPOSE, "config", "--format", "json"))["services"]["backend"]


def same_environment(service: dict, current: dict) -> None:
    live = dict(value.split("=", 1) for value in current["Config"]["Env"] if "=" in value)
    require(all(str(value) == live.get(key) for key, value in service["environment"].items()), "compose_environment_drift")
    for key, default in (("command", current["Config"].get("Cmd")), ("entrypoint", current["Config"].get("Entrypoint"))):
        if key in service and service[key] is not None:
            require(service[key] == default, "compose_startup_drift")


def backup_evidence() -> bool:
    if BACKUP_EVIDENCE_FILE is None:
        return False
    regular_file(BACKUP_EVIDENCE_FILE, private=True)
    evidence = json.loads(BACKUP_EVIDENCE_FILE.read_bytes())
    require(evidence.get("version") == 1 and evidence.get("schema") == START_SCHEMA
            and evidence.get("source_image") == CURRENT_ID
            and evidence.get("encrypted") is True and evidence.get("restore_verified") is True,
            "backup_evidence_invalid")
    try:
        backup_at = datetime.fromisoformat(evidence["backup_completed_at"])
        restored_at = datetime.fromisoformat(evidence["restore_verified_at"])
        now = datetime.now(UTC)
        require(backup_at.utcoffset() is not None and restored_at.utcoffset() is not None
                and 0 <= (now - backup_at).total_seconds() <= BACKUP_MAX_AGE_SECONDS
                and backup_at <= restored_at <= now, "backup_evidence_stale")
    except (KeyError, TypeError, ValueError):
        raise ReleaseError("backup_evidence_invalid") from None
    archive = Path(evidence.get("artifact_path", ""))
    regular_file(archive, private=True)
    require(archive.stat().st_size > 0 and digest(archive) == evidence.get("artifact_sha256"), "backup_artifact_mismatch")
    return True


def preflight() -> dict:
    require(os.getuid() == OWNER_UID and os.isatty(0), "native_owner_terminal_required")
    for path in (ENV_FILE, PLAN_FILE):
        regular_file(path)
    if LOCK_VERIFIED:
        regular_file(LOCK_FILE)
    for path in (COMPOSE_DIR / "compose.yaml", COMPOSE_DIR / "no-memcg.yaml", CANARY_FILE, SCRIPT_FILE):
        regular_file(path, owner=None)
    require(digest(CANARY_FILE) == CANARY_SHA256, "canary_source_drift")
    env_bytes, plan_bytes = ENV_FILE.read_bytes(), PLAN_FILE.read_bytes()
    plan = json.loads(plan_bytes)
    require(plan.get("expected_image") == CURRENT_ID and plan.get("readiness_required") is True, "watchdog_plan_drift")
    require(len(re.findall(r"(?m)^SELLORA_IMAGE=" + re.escape(CURRENT_TAG) + r"[ \t]*$", env_bytes.decode())) == 1, "deployment_image_drift")
    for tag, image_id, source in ((CURRENT_TAG, CURRENT_ID, CURRENT_SOURCE),
                                  (CANDIDATE_TAG, CANDIDATE_ID, CANDIDATE_SOURCE), (BRIDGE_TAG, BRIDGE_ID, BRIDGE_SOURCE)):
        image(tag, image_id, source)
    require(healthy(CURRENT_ID) and schema() == START_SCHEMA, "current_runtime_drift")
    current, service = container(), compose_config()
    require(service.get("image") == CURRENT_TAG, "compose_image_drift")
    same_environment(service, current)
    units = {SERVICE_UNIT: unit_state(SERVICE_UNIT)}
    observed_timers = units[SERVICE_UNIT].get("TriggeredBy", "").split()
    require(all(re.fullmatch(r"[A-Za-z0-9_.@:-]+\.timer", value) for value in observed_timers), "unrecognized_trigger")
    missing = []
    if TIMER_UNIT is None:
        missing.append("watchdog_timer_pin")
    else:
        require(observed_timers == [TIMER_UNIT], "watchdog_trigger_drift")
        units[TIMER_UNIT] = unit_state(TIMER_UNIT)
    for name, state in units.items():
        if UNIT_PINS.get(name) != (state["FragmentPath"], state["sha256"]):
            missing.append("watchdog_unit_source_pin")
        if state.get("DropInPaths", ""):
            missing.append("watchdog_dropin_review")
        if state.get("NeedDaemonReload") != "no":
            missing.append("watchdog_loaded_source_verification")
    if not LOCK_VERIFIED:
        missing.append("watchdog_lock_verification")
    if not IMAGE_REHEARSALS_VERIFIED:
        missing.append("image_rehearsals")
    if not BACKUP_MECHANISM_VERIFIED:
        missing.append("backup_mechanism_verification")
    if not backup_evidence():
        missing.append("encrypted_backup_restore_evidence")
    return {"env": env_bytes, "plan_bytes": plan_bytes, "plan": plan, "current": current,
            "units": units, "observed_timers": observed_timers, "missing": sorted(set(missing))}


def atomic_write(path: Path, data: bytes) -> None:
    require(path in (ENV_FILE, PLAN_FILE), "write_path_not_allowed")
    regular_file(path)
    fd, name = tempfile.mkstemp(prefix=".sellora-s8-update-", dir=path.parent)
    try:
        os.fchmod(fd, stat.S_IMODE(path.stat().st_mode))
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def pointers(snapshot: dict, tag: str, image_id: str) -> None:
    env = re.sub(r"(?m)^SELLORA_IMAGE=" + re.escape(CURRENT_TAG) + r"[ \t]*$",
                 "SELLORA_IMAGE=" + tag, snapshot["env"].decode()).encode()
    plan = dict(snapshot["plan"], expected_image=image_id)
    atomic_write(ENV_FILE, env)
    atomic_write(PLAN_FILE, (json.dumps(plan, ensure_ascii=False, indent=2) + "\n").encode())
    require(ENV_FILE.read_bytes() == env and json.loads(PLAN_FILE.read_bytes()) == plan, "pointer_verification_failed")
    service = compose_config()
    require(service.get("image") == tag, "compose_image_drift")
    same_environment(service, snapshot["current"])


def save_configs(snapshot: dict) -> None:
    for path, content in ((ENV_FILE, snapshot["env"]), (PLAN_FILE, snapshot["plan_bytes"])):
        fd, name = tempfile.mkstemp(prefix=".sellora-s8-before-", dir=path.parent)
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())


def recreate() -> None:
    command(*COMPOSE, "up", "-d", "--no-deps", "--force-recreate", "--pull", "never", "backend")


def canary() -> str:
    require(http_code("/api/v1/workspaces/current/subscription", {"X-Workspace-ID": str(uuid4())}) == 401,
            "unauthenticated_canary_failed")
    names = ("WORKSPACE_ID", "OWNER_TOKEN", "MANAGER_TOKEN", "ANALYST_TOKEN", "FOREIGN_WORKSPACE_ID")
    if not all(os.getenv("SELLORA_CANARY_" + name) for name in names):
        return "MISSING"
    require(digest(CANARY_FILE) == CANARY_SHA256, "canary_source_drift")
    env = {key: value for key, value in os.environ.items() if key in {"PATH", "LANG", "LC_ALL"}
           or key in {"SELLORA_CANARY_" + name for name in names}}
    env["SELLORA_CANARY_API_URL"] = API_ORIGIN
    result = json.loads(command(sys.executable, str(CANARY_FILE), "--expected-status", "UNMANAGED", "--require-denials", env=env))
    require(result.get("result") == "PASS" and result.get("skipped") == [], "authenticated_canary_failed")
    return "PASS"


def apply(snapshot: dict) -> dict:
    require(not snapshot["missing"], "unresolved_preflight_gates")
    timer_active = snapshot["units"][TIMER_UNIT]["ActiveState"] == "active"
    staged, safe_pointers, timer_restored = False, True, False
    try:
        command("systemctl", "--user", "stop", TIMER_UNIT, SERVICE_UNIT)
        require(all(unit_state(name)["ActiveState"] == "inactive" for name in (TIMER_UNIT, SERVICE_UNIT)), "watchdog_not_quiesced")
        lock_fd = os.open(LOCK_FILE, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(lock_fd, "rb") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            safe_pointers = False
            require(ENV_FILE.read_bytes() == snapshot["env"] and PLAN_FILE.read_bytes() == snapshot["plan_bytes"], "configuration_changed")
            require(healthy(CURRENT_ID) and schema() == START_SCHEMA, "current_runtime_drift")
            require(backup_evidence(), "encrypted_backup_restore_evidence_missing")
            safe_pointers = True
            save_configs(snapshot)
            try:
                staged, safe_pointers = True, False
                pointers(snapshot, BRIDGE_TAG, BRIDGE_ID)
                safe_pointers = True
                recreate()
                wait_for(BRIDGE_ID, START_SCHEMA)
                # The rehearsed bridge env.py wraps the complete 049->052 chain
                # in one PostgreSQL transaction. Its startup never migrates.
                command("docker", "exec", "--workdir", "/app", CONTAINER, "python", "-m", "alembic", "upgrade", TARGET_SCHEMA, timeout=180)
                require(schema() == TARGET_SCHEMA, "migration_revision_mismatch")
                safe_pointers = False
                pointers(snapshot, CANDIDATE_TAG, CANDIDATE_ID)
                safe_pointers = True
                recreate()
                wait_for(CANDIDATE_ID, TARGET_SCHEMA)
                strict = canary()
                if timer_active:
                    command("systemctl", "--user", "start", TIMER_UNIT)
                    require(unit_state(TIMER_UNIT)["ActiveState"] == "active", "timer_restore_failed")
                    timer_restored = True
                return {"result": "APPLIED", "readiness": "PASS", "unauthenticated_canary": "PASS", "authenticated_canary": strict}
            except BaseException:
                if staged:
                    safe_pointers = False
                    try:
                        command("systemctl", "--user", "stop", TIMER_UNIT, SERVICE_UNIT)
                        require(all(unit_state(name)["ActiveState"] == "inactive" for name in (TIMER_UNIT, SERVICE_UNIT)), "watchdog_not_quiesced")
                        pointers(snapshot, BRIDGE_TAG, BRIDGE_ID)
                        safe_pointers = True
                        recreate()
                        require(schema() in {START_SCHEMA, TARGET_SCHEMA}, "rollback_revision_unsupported")
                        wait_for(BRIDGE_ID, schema())
                    except BaseException:
                        raise ReleaseError("bridge_recovery_unconfirmed") from None
                raise
    finally:
        # Never reactivate recovery against an unverified pair of pointers.
        if timer_active and safe_pointers and not timer_restored:
            command("systemctl", "--user", "start", TIMER_UNIT)
            require(unit_state(TIMER_UNIT)["ActiveState"] == "active", "timer_restore_failed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--apply", action="store_true")
    group.add_argument("--inspect-services", action="store_true")
    args = parser.parse_args(argv)
    handlers = {}
    def interrupt(signum, frame):
        raise KeyboardInterrupt
    try:
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            handlers[signum] = signal.signal(signum, interrupt)
        if args.inspect_services:
            result = inspect_services()
        else:
            snapshot = preflight()
            if args.apply:
                result = apply(snapshot)
            else:
                result = {"result": "PREFLIGHT_BLOCKED" if snapshot["missing"] else "PREFLIGHT_PASS",
                          "missing": snapshot["missing"], "observed_timers": snapshot["observed_timers"],
                          "units": {name: {key: state[key] for key in ("Id", "ActiveState", "FragmentPath", "sha256", "DropInPaths", "NeedDaemonReload")}
                                    for name, state in snapshot["units"].items()}}
    except KeyboardInterrupt:
        result = {"result": "FAILED", "check": "interrupted"}
    except ReleaseError as exc:
        result = {"result": "FAILED", "check": str(exc)}
        if isinstance(exc, UnsafeFilePermissions):
            result["file"] = exc.file_metadata
    except Exception:
        result = {"result": "FAILED", "check": "unexpected_error"}
    finally:
        for signum, handler in handlers.items():
            signal.signal(signum, handler)
    print(json.dumps(result))
    if result["result"] in {"FAILED", "PREFLIGHT_BLOCKED"}:
        return 1
    return 2 if result.get("authenticated_canary") == "MISSING" else 0


if __name__ == "__main__":
    raise SystemExit(main())
