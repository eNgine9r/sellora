"""Tempfile-only source handoff tests: no native services or production input."""
import hashlib
import importlib.util
import json
import os
import errno
from pathlib import Path
import stat

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "deploy/raspberry/sellora_s8_source_review.py"
spec = importlib.util.spec_from_file_location("s8_source_review", SCRIPT)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


@pytest.fixture
def native(tmp_path, monkeypatch):
    units, scripts = tmp_path / ".config/systemd/user", tmp_path / ".local/bin"
    units.mkdir(parents=True)
    scripts.mkdir(parents=True)
    for key, value in {"OWNER_UID": os.getuid(), "OWNER_HOME": tmp_path, "UNIT_DIR": units, "SCRIPT_DIR": scripts}.items():
        monkeypatch.setattr(review, key, value)
    monkeypatch.setattr(review.os, "isatty", lambda descriptor: True)
    for name in review.UNIT_NAMES:
        if name.endswith(".service"):
            script = scripts / (name.removesuffix(".service") + ".py")
            script.write_text("#!/usr/bin/python3\nraise RuntimeError('MUST NEVER EXECUTE SOURCE')\n")
            text = f"[Service]\nExecStart=/usr/bin/python3 {script}\n"
        else:
            text = "[Timer]\nUnit=" + name.removesuffix(".timer") + ".service\n"
        (units / name).write_text(text)
    monkeypatch.setattr(review, "WATCHDOG_HASHES", {
        name: hashlib.sha256((units / name).read_bytes()).hexdigest() for name in review.WATCHDOG_HASHES
    })
    return tmp_path, units, scripts


def invoke(capsys):
    code = review.main(["--prepare"])
    output = capsys.readouterr()
    assert output.err == "" and len(output.out.splitlines()) == 1
    return code, json.loads(output.out), output.out


def test_private_single_draft_contains_only_fixed_units_and_direct_scripts(native, monkeypatch, capsys):
    home, units, scripts = native
    seen, original = [], review.read_source
    def read(path, limit):
        seen.append(path)
        return original(path, limit)
    monkeypatch.setattr(review, "read_source", read)
    code, result, output = invoke(capsys)
    assert code == 0 and result["result"] == "SOURCE_REVIEW_DRAFT" and result["review_required"] is True
    artifact = Path(result["artifact_path"])
    assert artifact.parent.parent == home and artifact.name == "review.md"
    assert stat.S_IMODE(artifact.stat().st_mode) == 0o600 and stat.S_IMODE(artifact.parent.stat().st_mode) == 0o700
    assert list(artifact.parent.iterdir()) == [artifact]
    assert seen[:8] == [units / name for name in review.UNIT_NAMES]
    assert set(seen[8:]) == set(scripts.iterdir()) and len(result["files"]) == 12
    assert "MUST NEVER EXECUTE SOURCE" in artifact.read_text() and "MUST NEVER EXECUTE SOURCE" not in output
    assert "may still contain inline secrets" in artifact.read_text()
    assert {item["code"] for item in result["unresolved_dependencies"]} >= {"transitive_dependencies_not_collected"}
    assert all(item["sha256"] == hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest() for item in result["files"])


@pytest.mark.parametrize("guard", ["uid", "tty"])
def test_requires_native_owner_terminal_before_any_read(native, monkeypatch, capsys, guard):
    monkeypatch.setattr(review, "OWNER_UID", os.getuid() + 1 if guard == "uid" else os.getuid())
    monkeypatch.setattr(review.os, "isatty", lambda descriptor: guard != "tty")
    monkeypatch.setattr(review, "read_source", lambda *args: pytest.fail("Read before owner guard"))
    assert invoke(capsys)[:2] == (1, {"result": "FAILED", "check": "native_owner_terminal_required"})


def test_watchdog_original_drift_blocks_before_draft_creation(native, capsys):
    home, units, _ = native
    (units / "sellora-runtime-health-watchdog.service").write_text("SYNTHETIC_SECRET_CHANGED_SOURCE")
    code, result, output = invoke(capsys)
    assert code == 1 and result == {"result": "FAILED", "check": "watchdog_source_changed"}
    assert "SYNTHETIC_SECRET" not in output and list(home.glob("sellora-s8-source-review-*")) == []


@pytest.mark.parametrize("kind", ["file", "ancestor", "fifo"])
def test_unsafe_required_sources_fail_without_following_or_blocking(native, capsys, kind):
    _, units, _ = native
    path = units / "sellora-runtime-health-watchdog.service"
    if kind == "ancestor":
        saved = units.with_name("original")
        units.rename(saved)
        units.symlink_to(saved, target_is_directory=True)
    else:
        path.unlink()
        if kind == "fifo":
            os.mkfifo(path)
        else:
            path.symlink_to(units / "sellora-db-backup.service")
    code, result, _ = invoke(capsys)
    assert code == 1 and result["check"] in {"source_unavailable_or_unsafe", "source_not_regular"}


def test_multiline_environment_credentials_and_unsupported_commands_are_redacted(native, capsys):
    _, units, _ = native
    path = units / "sellora-db-backup.service"
    with path.open("a") as handle:
        handle.write('Environment=TOKEN=SYNTHETIC_PRIVATE_A \\\n PASSWORD=SYNTHETIC_PRIVATE_B\n'
                     'SetCredential=secret:SYNTHETIC_PRIVATE_C\nEnvironmentFile=/private/credential.env\n'
                     'ExecStartPost=/bin/sh -c "echo SYNTHETIC_PRIVATE_D"\n')
    code, result, output = invoke(capsys)
    draft = Path(result["artifact_path"]).read_text()
    assert code == 0 and "SYNTHETIC_PRIVATE" not in draft + output
    assert "/private/credential.env" not in draft + output
    metadata = next(item for item in result["files"] if item["path"] == str(path))
    assert {item["directive"] for item in metadata["redactions"]} == {"Environment", "SetCredential", "EnvironmentFile", "ExecStartPost"}
    assert any(item["code"] == "unsupported_invocation" for item in result["unresolved_dependencies"])


def test_script_secret_assignments_redacted_and_transitive_references_not_followed(native, capsys):
    home, _, scripts = native
    outside = home / "outside.py"
    outside.write_text("SYNTHETIC_TRANSITIVE_SECRET")
    path = scripts / "sellora-db-backup.py"
    path.write_text(f'#!/usr/bin/python3\nAPI_KEY = "SYNTHETIC_PRIVATE"\nsource = "{outside}"\n')
    code, result, output = invoke(capsys)
    draft = Path(result["artifact_path"]).read_text()
    assert code == 0 and "SYNTHETIC_PRIVATE" not in draft + output and "SYNTHETIC_TRANSITIVE_SECRET" not in draft
    assert str(outside) not in [item["path"] for item in result["files"]]
    metadata = next(item for item in result["files"] if item["path"] == str(path))
    assert metadata["redactions"] == [{"line": 2, "reason": "possible_inline_credential"}]


def test_ambiguous_multiline_script_secret_omits_remainder(native, capsys):
    _, _, scripts = native
    (scripts / "sellora-db-backup.py").write_text("#!/usr/bin/python3\nSECRET = '''\nSYNTHETIC_PRIVATE\n'''\n")
    _, result, output = invoke(capsys)
    assert "SYNTHETIC_PRIVATE" not in Path(result["artifact_path"]).read_text() + output


@pytest.mark.parametrize("invocation", ["/bin/sh -c 'dynamic'", "/usr/bin/env python3 $SCRIPT", "/usr/bin/python3 /outside/sellora.py",
                                        "/usr/bin/python3 /home/btcradar/.config/sellora/deployment.env"])
def test_outside_dynamic_inline_references_are_not_collected(native, capsys, invocation):
    _, units, scripts = native
    (units / "sellora-db-backup.service").write_text("[Service]\nExecStart=" + invocation + "\n")
    _, result, _ = invoke(capsys)
    assert len(result["files"]) == 11
    assert all(Path(item["path"]).parent in {units, scripts} for item in result["files"])
    assert any(item["code"] == "unsupported_invocation" for item in result["unresolved_dependencies"])


@pytest.mark.parametrize("kind,expected", [("binary", "source_not_text"), ("oversize", "source_too_large"), ("extensionless", "unsupported_script_shebang")])
def test_invalid_direct_script_is_bounded_omission(native, capsys, kind, expected):
    _, units, scripts = native
    name = "sellora-db-backup" if kind == "extensionless" else "sellora-db-backup.py"
    path = scripts / name
    path.write_bytes(b"\x00synthetic" if kind == "binary" else b"x" * (review.SCRIPT_LIMIT + 1) if kind == "oversize" else b"not a script\n")
    (units / "sellora-db-backup.service").write_text(f"[Service]\nExecStart={path}\n")
    _, result, output = invoke(capsys)
    assert any(item == {"path": str(path), "code": expected} for item in result["unresolved_dependencies"])
    assert "synthetic" not in output


def test_total_byte_budget_fails_before_writing(native, monkeypatch, capsys):
    monkeypatch.setattr(review, "TOTAL_LIMIT", 1)
    assert invoke(capsys)[:2] == (1, {"result": "FAILED", "check": "source_total_limit"})


def test_direct_script_count_budget_fails_before_writing(native, monkeypatch, capsys):
    monkeypatch.setattr(review, "SCRIPT_COUNT_LIMIT", 0)
    assert invoke(capsys)[:2] == (1, {"result": "FAILED", "check": "source_count_limit"})


def test_missing_backup_unit_and_symlinked_script_remain_explicit_omissions(native, capsys):
    home, units, scripts = native
    missing = units / "sellora-google-drive-backup.timer"
    missing.unlink()
    outside = home / "private-source.py"
    outside.write_text("SYNTHETIC_PRIVATE_OUTSIDE_CONTENT")
    source = scripts / "sellora-db-backup.py"
    source.unlink()
    source.symlink_to(outside)
    code, result, output = invoke(capsys)
    assert code == 0
    assert {"path": str(missing), "code": "source_missing"} in result["unresolved_dependencies"]
    assert {"path": str(source), "code": "source_unavailable_or_unsafe"} in result["unresolved_dependencies"]
    assert "SYNTHETIC_PRIVATE" not in Path(result["artifact_path"]).read_text() + output


def test_env_state_and_arbitrary_paths_cannot_be_read(native):
    home, units, scripts = native
    for path in (home / "deployment.env", scripts / "sellora-secrets.env", units / "unrelated.service", scripts / "nested/sellora.py"):
        with pytest.raises(review.ReviewError, match="source_path_not_allowed"):
            review.read_source(path, 100)


def test_exclusive_create_failure_preserves_other_owners_file(native, monkeypatch, capsys):
    home, _, _ = native
    original_open = review.os.open
    def raced_open(path, flags, mode=0o777, *, dir_fd=None):
        if path == "review.md" and flags & os.O_EXCL:
            descriptor = original_open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=dir_fd)
            os.write(descriptor, b"SYNTHETIC_PREEXISTING_SENTINEL")
            os.close(descriptor)
            raise FileExistsError(errno.EEXIST, "SYNTHETIC_PRIVATE_ERROR")
        return original_open(path, flags, mode, dir_fd=dir_fd)
    monkeypatch.setattr(review.os, "open", raced_open)
    code, result, output = invoke(capsys)
    assert code == 1 and result == {"result": "FAILED", "check": "source_review_failed"}
    assert "SYNTHETIC" not in output
    files = list(home.glob("sellora-s8-source-review-*/review.md"))
    assert len(files) == 1 and files[0].read_bytes() == b"SYNTHETIC_PREEXISTING_SENTINEL"


@pytest.mark.parametrize("fault", ["write", "fsync"])
def test_output_failure_removes_only_our_new_partial_file(native, monkeypatch, capsys, fault):
    home, units, _ = native
    before = {path: path.read_bytes() for path in units.iterdir()}
    if fault == "fsync":
        def fail_sync(descriptor):
            raise OSError("SYNTHETIC_PRIVATE_ERROR")
        monkeypatch.setattr(review.os, "fsync", fail_sync)
    else:
        original_fdopen = review.os.fdopen
        class BrokenWriter:
            def __init__(self, descriptor):
                self.file = original_fdopen(descriptor, "wb")
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.file.close()
            def write(self, data):
                self.file.write(data[:20])
                raise OSError("SYNTHETIC_PRIVATE_ERROR")
        def fdopen(descriptor, mode):
            return BrokenWriter(descriptor) if mode == "wb" else original_fdopen(descriptor, mode)
        monkeypatch.setattr(review.os, "fdopen", fdopen)
    code, result, output = invoke(capsys)
    assert code == 1 and result == {"result": "FAILED", "check": "source_review_failed"}
    assert "SYNTHETIC" not in output
    assert list(home.glob("sellora-s8-source-review-*/review.md")) == []
    assert {path: path.read_bytes() for path in units.iterdir()} == before
