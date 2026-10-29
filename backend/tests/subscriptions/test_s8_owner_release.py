"""Fake-runner tests only: no Docker, systemd, live credentials or live database."""
import importlib.util
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "deploy/raspberry/sellora_s8_subscription_release.py"
spec = importlib.util.spec_from_file_location("s8_owner_release", SCRIPT)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
REAL_COMMAND = release.command


@pytest.fixture
def target(tmp_path, monkeypatch):
    monkeypatch.setattr(release, "OWNER_UID", os.getuid())
    monkeypatch.setattr(release.os, "isatty", lambda fd: True)
    env, plan, lock = (tmp_path / name for name in ("deployment.env", "api-watchdog.json", "api-watchdog.lock"))
    env.write_text(f"SELLORA_IMAGE={release.CURRENT_TAG}\nPRIVATE_VALUE=synthetic-secret\n")
    plan.write_text(json.dumps({"expected_image": release.CURRENT_ID, "readiness_required": True, "other": "preserved"}))
    lock.touch()
    for path in (env, plan, lock):
        path.chmod(0o600)
    for name, value in {"ENV_FILE": env, "PLAN_FILE": plan, "LOCK_FILE": lock, "COMPOSE_DIR": tmp_path,
                        "COMPOSE": ("docker", "compose", "--synthetic-fixture"), "LOCK_VERIFIED": True,
                        "TIMER_UNIT": "synthetic-watchdog.timer", "BACKUP_MECHANISM_VERIFIED": True}.items():
        monkeypatch.setattr(release, name, value)
    for name in ("compose.yaml", "no-memcg.yaml"):
        (tmp_path / name).touch()
    units, pins = {}, {}
    for name in (release.SERVICE_UNIT, release.TIMER_UNIT):
        fragment = tmp_path / name
        fragment.write_text("synthetic unit fixture\n")
        units[name] = {"Id": name, "LoadState": "loaded", "ActiveState": "active" if name == release.TIMER_UNIT else "inactive",
                       "FragmentPath": str(fragment), "TriggeredBy": release.TIMER_UNIT if name == release.SERVICE_UNIT else "",
                       "Triggers": release.SERVICE_UNIT if name == release.TIMER_UNIT else "",
                       "DropInPaths": "", "NeedDaemonReload": "no"}
        pins[name] = (str(fragment), release.digest(fragment))
    monkeypatch.setattr(release, "UNIT_PINS", pins)
    archive, evidence = tmp_path / "synthetic-backup.enc", tmp_path / "backup-evidence.json"
    archive.write_bytes(b"synthetic encrypted artifact; no production contents")
    now = datetime.now(UTC)
    evidence.write_text(json.dumps({"version": 1, "schema": release.START_SCHEMA, "source_image": release.CURRENT_ID,
        "encrypted": True, "restore_verified": True, "backup_completed_at": (now - timedelta(minutes=2)).isoformat(),
        "restore_verified_at": (now - timedelta(minutes=1)).isoformat(), "artifact_path": str(archive),
        "artifact_sha256": release.digest(archive)}))
    archive.chmod(0o600)
    evidence.chmod(0o600)
    monkeypatch.setattr(release, "BACKUP_EVIDENCE_FILE", evidence)
    state = SimpleNamespace(image=release.CURRENT_ID, schema=release.START_SCHEMA, units=units, calls=[], phases=[],
                            failure=None, timer_failure=False, timer_stuck=False, evidence=evidence, env=env, plan=plan,
                            strict=False, strict_failure=False, observed=[])
    images = {tag: {"Id": image_id, "Architecture": "arm64", "Os": "linux", "Config": {
        "Labels": {"org.opencontainers.image.revision": source}, "User": "10001:10001", "Cmd": ["python", "scripts/start_raspberry.py"]}}
        for tag, image_id, source in ((release.CURRENT_TAG, release.CURRENT_ID, release.CURRENT_SOURCE),
                                     (release.BRIDGE_TAG, release.BRIDGE_ID, release.BRIDGE_SOURCE),
                                     (release.CANDIDATE_TAG, release.CANDIDATE_ID, release.CANDIDATE_SOURCE))}
    state.images = images
    current_config = {"Env": ["PRIVATE_VALUE=synthetic-secret"], "Cmd": ["python", "-c", "synthetic resource wrapper"], "Entrypoint": None}
    def tag():
        return env.read_text().splitlines()[0].split("=", 1)[1]
    def fail_once(phase):
        state.phases.append(phase)
        if state.failure == phase:
            state.failure = None
            raise release.ReleaseError("synthetic_failure")
        if state.failure == "interrupt_" + phase:
            state.failure = None
            raise KeyboardInterrupt
    def command(*args, **kwargs):
        state.calls.append(args)
        if args[:3] == ("systemctl", "--user", "show"):
            return "\n".join(f"{key}={value}" for key, value in units[args[-1]].items())
        if args[:3] == ("systemctl", "--user", "stop"):
            assert args[3:] == (release.TIMER_UNIT, release.SERVICE_UNIT)
            for name in args[3:]:
                units[name]["ActiveState"] = "inactive"
            if state.timer_stuck:
                units[release.SERVICE_UNIT]["ActiveState"] = "active"
            return ""
        if args[:3] == ("systemctl", "--user", "start"):
            assert args[3:] == (release.TIMER_UNIT,)
            if state.timer_failure:
                state.timer_failure = False
                raise release.ReleaseError("synthetic_timer_failure")
            units[release.TIMER_UNIT]["ActiveState"] = "active"
            return ""
        if args[:3] == ("docker", "image", "inspect"):
            return json.dumps([images[args[-1]]])
        if args[:2] == ("docker", "inspect"):
            return json.dumps([{"Image": state.image, "State": {"Health": {"Status": "healthy"}}, "Config": current_config}])
        if args[:len(release.COMPOSE)] == release.COMPOSE:
            if "config" in args:
                return json.dumps({"services": {"backend": {"image": tag(), "environment": {"PRIVATE_VALUE": "synthetic-secret"},
                                                             "command": current_config["Cmd"]}}})
            assert args[-7:] == ("up", "-d", "--no-deps", "--force-recreate", "--pull", "never", "backend")
            image_id = images[tag()]["Id"]
            assert json.loads(plan.read_bytes())["expected_image"] == image_id
            state.image = image_id
            state.observed.append((image_id, state.schema))
            fail_once("bridge" if image_id == release.BRIDGE_ID else "candidate")
            return ""
        if args[:2] == ("docker", "exec"):
            if "-m" in args:
                assert state.image == release.BRIDGE_ID and state.schema == release.START_SCHEMA
                assert json.loads(plan.read_bytes())["expected_image"] == release.BRIDGE_ID
                fail_once("before_migration")
                state.schema = release.TARGET_SCHEMA
                fail_once("after_migration")
                return ""
            return json.dumps({"heads": [state.schema], "superuser": False, "bypassrls": True})
        if args[0] == release.sys.executable:
            assert kwargs["env"]["SELLORA_CANARY_API_URL"] == release.API_ORIGIN
            assert "synthetic-token" not in " ".join(args)
            if state.strict_failure:
                raise release.ReleaseError("synthetic_canary_failure")
            return json.dumps({"result": "PASS", "skipped": []})
        raise AssertionError("Unexpected fake command")
    monkeypatch.setattr(release, "command", command)
    monkeypatch.setattr(release, "http_code", lambda path, headers=None: 401 if "subscription" in path else 200)
    monkeypatch.setattr(release.time, "sleep", lambda value: None)
    for name in ("WORKSPACE_ID", "OWNER_TOKEN", "MANAGER_TOKEN", "ANALYST_TOKEN", "FOREIGN_WORKSPACE_ID"):
        monkeypatch.delenv("SELLORA_CANARY_" + name, raising=False)
    return state


def assert_bridge(target, schema):
    assert release.BRIDGE_TAG in target.env.read_text()
    assert json.loads(target.plan.read_bytes())["expected_image"] == release.BRIDGE_ID
    assert target.image == release.BRIDGE_ID and target.schema == schema
    assert target.units[release.TIMER_UNIT]["ActiveState"] == "active"


def test_default_preflight_has_no_mutations(target, capsys):
    before = target.env.read_bytes(), target.plan.read_bytes()
    assert release.main([]) == 0
    output = capsys.readouterr().out
    assert json.loads(output)["result"] == "PREFLIGHT_PASS"
    assert "synthetic-secret" not in output
    assert (target.env.read_bytes(), target.plan.read_bytes()) == before
    assert not any("stop" in args or "up" in args or "upgrade" in args for args in target.calls)


@pytest.mark.parametrize("kind", ["compose.yaml", "no-memcg.yaml", "unit", "private_evidence"])
@pytest.mark.parametrize("args", [[], ["--preflight"], ["--apply"]])
def test_unsafe_permissions_report_only_file_metadata_without_mutation(target, capsys, kind, args):
    if kind == "unit":
        path = Path(target.units[release.SERVICE_UNIT]["FragmentPath"])
    elif kind == "private_evidence":
        path = target.evidence
    else:
        path = release.COMPOSE_DIR / kind
    path.chmod(0o640 if kind == "private_evidence" else 0o664)
    before = (path.read_bytes(), path.stat(), target.env.read_bytes(), target.plan.read_bytes())
    assert release.main(args) == 1
    output = capsys.readouterr().out
    assert json.loads(output) == {
        "result": "FAILED", "check": "unsafe_file_permissions",
        "file": {"path": str(path), "mode": "0640" if kind == "private_evidence" else "0664",
                 "uid": before[1].st_uid, "gid": before[1].st_gid},
    }
    assert "synthetic-secret" not in output and "synthetic unit fixture" not in output
    after = path.stat()
    assert (path.read_bytes(), after.st_mode, after.st_uid, after.st_gid) == (
        before[0], before[1].st_mode, before[1].st_uid, before[1].st_gid,
    )
    assert (target.env.read_bytes(), target.plan.read_bytes()) == before[2:]
    assert not any("stop" in call or "start" in call or "up" in call or "upgrade" in call for call in target.calls)


def test_unknown_timer_is_observed_but_never_guessed_or_applied(target, monkeypatch, capsys):
    monkeypatch.setattr(release, "TIMER_UNIT", None)
    assert release.main(["--preflight"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["observed_timers"] == ["synthetic-watchdog.timer"]
    assert "watchdog_timer_pin" in result["missing"]
    assert release.main(["--apply"]) == 1
    assert not any("stop" in args or "up" in args for args in target.calls)


@pytest.mark.parametrize("gate", ["LOCK_VERIFIED", "IMAGE_REHEARSALS_VERIFIED", "BACKUP_EVIDENCE_FILE", "BACKUP_MECHANISM_VERIFIED"])
def test_missing_gate_blocks_apply_before_quiescing(target, monkeypatch, gate):
    monkeypatch.setattr(release, gate, None)
    with pytest.raises(release.ReleaseError, match="unresolved_preflight_gates"):
        release.apply(release.preflight())
    assert not any("stop" in args for args in target.calls)


@pytest.mark.parametrize("change", [{"LoadState": "not-found"}, {"Id": "unrecognized.service"}])
def test_unloaded_or_unknown_unit_prevents_mutation(target, change):
    target.units[release.SERVICE_UNIT].update(change)
    with pytest.raises(release.ReleaseError, match="unit_not_loaded_or_recognized"):
        release.preflight()
    assert not any("stop" in args for args in target.calls)


def test_native_watchdog_defaults_match_owner_observation():
    assert release.SERVICE_UNIT == "sellora-runtime-health-watchdog.service"
    assert release.TIMER_UNIT == "sellora-runtime-health-watchdog.timer"
    assert release.UNIT_PINS == {} and release.LOCK_VERIFIED is False
    assert release.BACKUP_MECHANISM_VERIFIED is False and release.BACKUP_EVIDENCE_FILE is None


@pytest.fixture
def observed_native_target(target, tmp_path, monkeypatch):
    """Literal native identities ensure the old, invented unit name cannot pass."""
    service, timer = "sellora-runtime-health-watchdog.service", "sellora-runtime-health-watchdog.timer"
    target.units.clear()
    pins = {}
    for name in (service, timer):
        fragment = tmp_path / name
        fragment.write_text("synthetic native-name unit; no deployed source\n")
        target.units[name] = {"Id": name, "LoadState": "loaded", "ActiveState": "inactive" if name == service else "active",
                              "FragmentPath": str(fragment), "TriggeredBy": timer if name == service else "",
                              "Triggers": service if name == timer else "", "DropInPaths": "", "NeedDaemonReload": "no"}
        pins[name] = (str(fragment), release.digest(fragment))
    monkeypatch.setattr(release, "TIMER_UNIT", timer)
    monkeypatch.setattr(release, "UNIT_PINS", pins)
    return target


def test_preflight_queries_literal_native_watchdog_pair(observed_native_target, capsys):
    assert release.main(["--preflight"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["result"] == "PREFLIGHT_PASS"
    assert result["observed_timers"] == ["sellora-runtime-health-watchdog.timer"]
    assert set(result["units"]) == {"sellora-runtime-health-watchdog.service", "sellora-runtime-health-watchdog.timer"}
    calls = [call for call in observed_native_target.calls if call[:3] == ("systemctl", "--user", "show")]
    assert [call[-1] for call in calls] == ["sellora-runtime-health-watchdog.service", "sellora-runtime-health-watchdog.timer"]


@pytest.mark.parametrize("name,state", [
    ("sellora-runtime-health-watchdog.service", "activating"),
    ("sellora-runtime-health-watchdog.service", "deactivating"),
    ("sellora-runtime-health-watchdog.service", "failed"),
    ("sellora-runtime-health-watchdog.timer", "activating"),
])
def test_transient_preflight_reports_all_gates_and_blocks_apply(observed_native_target, monkeypatch, capsys, name, state):
    observed_native_target.units[name]["ActiveState"] = state
    for key, value in {"UNIT_PINS": {}, "LOCK_VERIFIED": False, "BACKUP_MECHANISM_VERIFIED": False,
                       "BACKUP_EVIDENCE_FILE": None}.items():
        monkeypatch.setattr(release, key, value)
    before = observed_native_target.env.read_bytes(), observed_native_target.plan.read_bytes()
    for args in (["--preflight"], ["--apply"]):
        assert release.main(args) == 1
        result = json.loads(capsys.readouterr().out)
        if args == ["--preflight"]:
            assert result["result"] == "PREFLIGHT_BLOCKED"
            assert set(result["missing"]) == {"watchdog_unit_stability", "watchdog_unit_source_pin", "watchdog_lock_verification",
                                              "backup_mechanism_verification", "encrypted_backup_restore_evidence"}
            assert result["units"][name]["ActiveState"] == state
            for unit, metadata in result["units"].items():
                assert metadata["FragmentPath"] == observed_native_target.units[unit]["FragmentPath"]
                assert metadata["sha256"] == release.digest(Path(metadata["FragmentPath"]))
            assert result["units"]["sellora-runtime-health-watchdog.timer"]["Triggers"] == "sellora-runtime-health-watchdog.service"
        else:
            assert result == {"result": "FAILED", "check": "unresolved_preflight_gates"}
    assert (observed_native_target.env.read_bytes(), observed_native_target.plan.read_bytes()) == before
    assert not any("stop" in call or "start" in call or "up" in call or "upgrade" in call for call in observed_native_target.calls)
    with pytest.raises(release.ReleaseError, match="unit_not_stable"):
        release.unit_state(name)


@pytest.mark.parametrize("triggers", ["", "sellora-api-watchdog.service", "sellora-runtime-health-watchdog.service unrelated.service"])
def test_timer_must_reciprocally_trigger_only_verified_service(target, triggers):
    target.units[release.TIMER_UNIT]["Triggers"] = triggers
    with pytest.raises(release.ReleaseError, match="watchdog_target_drift"):
        release.preflight()
    assert not any("stop" in args or "start" in args or "up" in args for args in target.calls)


def test_unit_overrides_or_stale_loaded_source_block_apply(target):
    target.units[release.SERVICE_UNIT].update(DropInPaths="/synthetic/override.conf", NeedDaemonReload="yes")
    snapshot = release.preflight()
    assert "watchdog_dropin_review" in snapshot["missing"]
    assert "watchdog_loaded_source_verification" in snapshot["missing"]
    with pytest.raises(release.ReleaseError, match="unresolved_preflight_gates"):
        release.apply(snapshot)
    assert not any("stop" in args for args in target.calls)


@pytest.mark.parametrize("change", [{"restore_verified": False}, {"encrypted": False},
    {"backup_completed_at": (datetime.now(UTC) - timedelta(hours=2)).isoformat()}, {"artifact_sha256": "invalid"}])
def test_backup_evidence_is_mandatory_and_fresh(target, change):
    evidence = json.loads(target.evidence.read_bytes())
    evidence.update(change)
    target.evidence.write_text(json.dumps(evidence))
    with pytest.raises(release.ReleaseError):
        release.preflight()
    assert not any("stop" in args for args in target.calls)


def test_apply_stages_bridge_before_migration_and_reports_missing_auth_gate(target):
    result = release.apply(release.preflight())
    assert result["authenticated_canary"] == "MISSING" and result["unauthenticated_canary"] == "PASS"
    assert target.phases == ["bridge", "before_migration", "after_migration", "candidate"]
    assert target.observed == [(release.BRIDGE_ID, release.START_SCHEMA), (release.CANDIDATE_ID, release.TARGET_SCHEMA)]
    assert json.loads(target.plan.read_bytes())["other"] == "preserved"
    assert "PRIVATE_VALUE=synthetic-secret" in target.env.read_text()


@pytest.mark.parametrize("phase,schema", [("bridge", release.START_SCHEMA), ("before_migration", release.START_SCHEMA),
    ("after_migration", release.TARGET_SCHEMA), ("candidate", release.TARGET_SCHEMA),
    ("interrupt_bridge", release.START_SCHEMA), ("interrupt_after_migration", release.TARGET_SCHEMA)])
def test_failure_or_interrupt_restores_bridge_never_original(target, phase, schema):
    target.failure = phase
    with pytest.raises((release.ReleaseError, KeyboardInterrupt)):
        release.apply(release.preflight())
    assert_bridge(target, schema)
    assert all(image_id != release.CURRENT_ID for image_id, _ in target.observed)


def test_nonquiescent_watchdog_prevents_config_writes(target):
    target.timer_stuck = True
    before = target.env.read_bytes(), target.plan.read_bytes()
    with pytest.raises(release.ReleaseError, match="watchdog_not_quiesced"):
        release.apply(release.preflight())
    assert (target.env.read_bytes(), target.plan.read_bytes()) == before


def test_inactive_timer_remains_inactive(target):
    target.units[release.TIMER_UNIT]["ActiveState"] = "inactive"
    release.apply(release.preflight())
    assert target.units[release.TIMER_UNIT]["ActiveState"] == "inactive"
    assert not any("start" in args for args in target.calls)


def test_timer_restore_failure_also_recovers_bridge(target):
    target.timer_failure = True
    with pytest.raises(release.ReleaseError, match="synthetic_timer_failure"):
        release.apply(release.preflight())
    assert_bridge(target, release.TARGET_SCHEMA)


@pytest.mark.parametrize("tag,schema", [(release.BRIDGE_TAG, release.START_SCHEMA), (release.CANDIDATE_TAG, release.TARGET_SCHEMA)])
def test_partial_pointer_write_interrupt_recovers_bridge(target, monkeypatch, tag, schema):
    original = release.atomic_write
    failed = False
    def write(path, data):
        nonlocal failed
        if path == release.PLAN_FILE and tag in release.ENV_FILE.read_text() and not failed:
            failed = True
            raise KeyboardInterrupt
        original(path, data)
    monkeypatch.setattr(release, "atomic_write", write)
    with pytest.raises(KeyboardInterrupt):
        release.apply(release.preflight())
    assert_bridge(target, schema)


def test_candidate_readiness_failure_recovers_bridge(target, monkeypatch):
    original = release.healthy
    monkeypatch.setattr(release, "healthy", lambda image_id: False if image_id == release.CANDIDATE_ID else original(image_id))
    with pytest.raises(release.ReleaseError, match="readiness_failed"):
        release.apply(release.preflight())
    assert_bridge(target, release.TARGET_SCHEMA)


def test_compose_environment_strips_inherited_release_overrides(monkeypatch):
    captured = {}
    def run(args, **kwargs):
        captured.update(kwargs["env"])
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(release.subprocess, "run", run)
    monkeypatch.setenv("SELLORA_IMAGE", "synthetic-override")
    monkeypatch.setenv("SELLORA_CANARY_OWNER_TOKEN", "synthetic-token")
    monkeypatch.setenv("COMPOSE_FILE", "synthetic-override")
    REAL_COMMAND("docker", "compose", "config")
    assert not any(key.startswith(("SELLORA_", "COMPOSE_")) for key in captured)


def test_unexpected_exception_text_is_not_logged(target, monkeypatch, capsys):
    def fail():
        raise ValueError("synthetic-secret-from-error")
    monkeypatch.setattr(release, "preflight", fail)
    assert release.main([]) == 1
    assert json.loads(capsys.readouterr().out) == {"result": "FAILED", "check": "unexpected_error"}


def test_authenticated_probe_failure_recovers_bridge_without_secret_output(target, monkeypatch, capsys):
    for name in ("WORKSPACE_ID", "OWNER_TOKEN", "MANAGER_TOKEN", "ANALYST_TOKEN", "FOREIGN_WORKSPACE_ID"):
        monkeypatch.setenv("SELLORA_CANARY_" + name, "synthetic-token")
    target.strict_failure = True
    assert release.main(["--apply"]) == 1
    output = capsys.readouterr().out
    assert "synthetic-token" not in output and "synthetic-secret" not in output
    assert_bridge(target, release.TARGET_SCHEMA)


def test_native_owner_and_no_symlink_guards(target, monkeypatch):
    monkeypatch.setattr(release, "OWNER_UID", os.getuid() + 1)
    with pytest.raises(release.ReleaseError, match="native_owner_terminal_required"):
        release.preflight()
    monkeypatch.setattr(release, "OWNER_UID", os.getuid())
    actual = target.env.with_suffix(".actual")
    target.env.rename(actual)
    target.env.symlink_to(actual)
    with pytest.raises(release.ReleaseError, match="symlink_or_relative_path"):
        release.preflight()


@pytest.fixture
def service_inventory(monkeypatch):
    monkeypatch.setattr(release, "OWNER_UID", os.getuid())
    monkeypatch.setattr(release.os, "isatty", lambda fd: True)
    state = SimpleNamespace(calls=[], failure=None, many=False, show_failure=False, oversized=False)
    def forbidden(*args, **kwargs):
        raise AssertionError("Inspection attempted a non-inventory operation")
    for name in ("preflight", "apply", "regular_file", "atomic_write", "save_configs", "container", "schema"):
        monkeypatch.setattr(release, name, forbidden)
    def run(args, **kwargs):
        state.calls.append(args)
        assert args[0] == "systemctl" and args[1] in {"--user", "--system"}
        assert args[2] in {"list-unit-files", "list-units", "show"}
        assert "--no-ask-password" in args
        assert kwargs["stderr"] == release.subprocess.DEVNULL
        scope, action = args[1], args[2]
        if scope == "--user" and action == "list-unit-files" and state.failure:
            if state.failure == "unavailable":
                raise OSError("synthetic-secret")
            if state.failure == "timeout":
                raise release.subprocess.TimeoutExpired(args, 5, stderr="synthetic-secret")
            return SimpleNamespace(returncode=1, stdout="synthetic-secret", stderr="synthetic-secret")
        if action == "list-unit-files":
            names = ([f"sellora-backup-{index:03}.timer enabled" for index in range(30)] if state.many else [
                release.SERVICE_UNIT + " enabled", "sellora-api-watchdog.timer enabled",
                "sellora-db-backup.service static", "unrelated-backup.service enabled",
                "../sellora-watchdog.service enabled", "sellora-watchdog.service;bad enabled",
                "sellora-other.service enabled", "sellora-watchdog.service/invalid enabled",
            ])
            return SimpleNamespace(returncode=0, stdout="\n".join(names), stderr="")
        if action == "list-units":
            assert "--all" in args
            return SimpleNamespace(returncode=0, stdout="sellora-api-watchdog@synthetic.service loaded inactive dead\nsellora-api-watchdog.timer loaded active waiting", stderr="")
        assert args[-1].startswith("sellora") and args[-1].endswith((".service", ".timer"))
        assert "--property=" + ",".join(release.INSPECT_PROPERTIES) in args
        extra = "\nDropInPaths=" + "x" * 2049 if state.oversized else ""
        return SimpleNamespace(returncode=4 if state.show_failure and scope == "--user" else 0,
            stdout=f"Id={args[-1]}\nLoadState={'not-found' if scope == '--user' else 'loaded'}\nActiveState=inactive\nFragmentPath=/synthetic/unit\nUser=synthetic\nGroup=synthetic\nResult=success\nExecMainStatus=0\nEnvironment=synthetic-secret\nExecStart=synthetic-secret" + extra, stderr="")
    monkeypatch.setattr(release.subprocess, "run", run)
    return state


def test_native_service_inspection_reports_both_scopes_without_approving_or_mutating(service_inventory, capsys):
    before = release.TIMER_UNIT, dict(release.UNIT_PINS), release.LOCK_VERIFIED
    assert release.main(["--inspect-services"]) == 0
    output = capsys.readouterr()
    assert output.err == "" and len(output.out.splitlines()) == 1 and "synthetic-secret" not in output.out
    result = json.loads(output.out)
    assert result["result"] == "SERVICE_INSPECTION" and result["diagnostic_only"] is True
    assert [scope["scope"] for scope in result["scopes"]] == ["user", "system"]
    for scope in result["scopes"]:
        assert scope["known_units"] == [release.SERVICE_UNIT]
        assert scope["discovered_units"] == ["sellora-api-watchdog.timer", "sellora-api-watchdog@synthetic.service", "sellora-db-backup.service"]
        assert scope["units"][0]["fields"]["LoadState"] == ("not-found" if scope["scope"] == "user" else "loaded")
        assert all(set(unit["fields"]) <= set(release.INSPECT_PROPERTIES) for unit in scope["units"])
    assert (release.TIMER_UNIT, release.UNIT_PINS, release.LOCK_VERIFIED) == before


@pytest.mark.parametrize("failure,code", [("failed", "query_failed"), ("unavailable", "query_unavailable"), ("timeout", "query_timeout")])
def test_service_inspection_query_failures_are_bounded_observations(service_inventory, capsys, failure, code):
    service_inventory.failure = failure
    assert release.main(["--inspect-services"]) == 0
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result["scopes"][0]["queries"]["list-unit-files"]["code"] == code
    assert result["scopes"][1]["queries"]["list-unit-files"]["code"] == "ok"
    assert "synthetic-secret" not in output


def test_service_discovery_is_filtered_deduplicated_and_bounded(service_inventory, capsys):
    service_inventory.many = True
    assert release.main(["--inspect-services"]) == 0
    for scope in json.loads(capsys.readouterr().out)["scopes"]:
        assert len(scope["discovered_units"]) == release.INSPECT_UNIT_LIMIT and scope["discovery_truncated"] is True
        assert len(scope["units"]) == release.INSPECT_UNIT_LIMIT + 1
    assert len([call for call in service_inventory.calls if call[2] == "show"]) == 2 * (release.INSPECT_UNIT_LIMIT + 1)


def test_inspection_preserves_not_found_metadata_on_failed_show(service_inventory, capsys):
    service_inventory.show_failure = True
    assert release.main(["--inspect-services"]) == 0
    unit = json.loads(capsys.readouterr().out)["scopes"][0]["units"][0]
    assert unit["query"] == {"code": "query_failed", "exit_code": 4}
    assert unit["fields"]["LoadState"] == "not-found"


def test_inspection_omits_oversized_values(service_inventory, capsys):
    service_inventory.oversized = True
    assert release.main(["--inspect-services"]) == 0
    for scope in json.loads(capsys.readouterr().out)["scopes"]:
        for unit in scope["units"]:
            assert "DropInPaths" not in unit["fields"] and unit["oversized_fields"] == ["DropInPaths"]


@pytest.mark.parametrize("action,unit", [("restart", release.SERVICE_UNIT), ("show", "unrelated.service")])
def test_inventory_query_rejects_mutation_or_unrelated_names(service_inventory, action, unit):
    with pytest.raises(release.ReleaseError):
        release._inspect_query("user", action, unit)
    assert service_inventory.calls == []


@pytest.mark.parametrize("guard", ["uid", "tty"])
def test_service_inspection_retains_native_owner_guard(service_inventory, monkeypatch, capsys, guard):
    if guard == "uid":
        monkeypatch.setattr(release, "OWNER_UID", os.getuid() + 1)
    else:
        monkeypatch.setattr(release.os, "isatty", lambda fd: False)
    assert release.main(["--inspect-services"]) == 1
    assert json.loads(capsys.readouterr().out)["check"] == "native_owner_terminal_required"
    assert service_inventory.calls == []


@pytest.mark.parametrize("other", ["--apply", "--preflight"])
def test_service_inspection_cannot_be_combined_with_rollout_modes(service_inventory, other):
    with pytest.raises(SystemExit) as exc:
        release.main(["--inspect-services", other])
    assert exc.value.code == 2 and service_inventory.calls == []
