from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

SPEC = importlib.util.spec_from_file_location(
    "raspberry_startup", Path(__file__).parents[1] / "scripts" / "start_raspberry.py"
)
assert SPEC and SPEC.loader
startup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(startup)


def valid_environment():
    return {
        "DATABASE_URL": "postgresql+psycopg://test:test@database/sellora",
        "SECRET_KEY": "s" * 48,
        "JWT_SECRET": "j" * 48,
        "RENDER_GIT_COMMIT": "a" * 40,
    }


@pytest.mark.parametrize("field", ["DATABASE_URL", "SECRET_KEY", "JWT_SECRET", "RENDER_GIT_COMMIT"])
def test_missing_required_configuration_blocks_start(field):
    env = valid_environment()
    del env[field]
    with pytest.raises(startup.StartupError):
        startup.validate_environment(env)


@pytest.mark.parametrize("value", ["sqlite:///test.db", "postgresql://", "not-a-url"])
def test_non_postgres_or_incomplete_database_urls_are_rejected(value):
    env = valid_environment()
    env["DATABASE_URL"] = value
    with pytest.raises(startup.StartupError, match="INVALID_DATABASE_URL"):
        startup.validate_environment(env)


def test_existing_encryption_key_is_required_when_token_storage_is_active():
    env = valid_environment()
    env["META_TOKEN_STORAGE_ENABLED"] = "true"
    with pytest.raises(startup.StartupError, match="MISSING_META_TOKEN_ENCRYPTION_KEY"):
        startup.validate_environment(env)
    env["META_TOKEN_ENCRYPTION_KEY"] = "existing-key-preserved-for-migration"
    startup.validate_environment(env)


@pytest.mark.parametrize("actual", [(), ("old_revision",), ("current_revision", "other_revision")])
def test_unversioned_outdated_and_divergent_databases_block_start(actual):
    with pytest.raises(startup.StartupError, match="DATABASE_SCHEMA_MISMATCH"):
        startup.ensure_schema_current(("current_revision",), actual)


def test_matching_database_revision_is_accepted():
    startup.ensure_schema_current(("current_revision",), ("current_revision",))


def test_database_errors_never_expose_connection_details(monkeypatch, capsys):
    monkeypatch.setattr(startup, "image_revision", lambda: "a" * 40)
    monkeypatch.setattr(startup, "validate_environment", lambda env: None)
    monkeypatch.setattr(startup, "packaged_heads", lambda: ("head",))
    def fail():
        raise RuntimeError("postgresql://user:private-password@private-host/db")
    monkeypatch.setattr(startup, "database_heads", fail)
    assert startup.main() == 78
    output = capsys.readouterr().err
    assert "RuntimeError" in output
    assert "private-password" not in output
    assert "private-host" not in output


def test_no_server_is_started_when_schema_is_outdated(monkeypatch):
    monkeypatch.setattr(startup, "image_revision", lambda: "a" * 40)
    monkeypatch.setattr(startup, "validate_environment", lambda env: None)
    monkeypatch.setattr(startup, "packaged_heads", lambda: ("new",))
    monkeypatch.setattr(startup, "database_heads", lambda: ("old",))
    def forbidden(*args):
        pytest.fail("server must not start against the wrong schema")
    monkeypatch.setattr(startup.os, "execv", forbidden)
    assert startup.main() == 78


def test_success_starts_one_worker_without_query_string_access_logs(monkeypatch):
    monkeypatch.setattr(startup, "image_revision", lambda: "a" * 40)
    monkeypatch.setattr(startup, "validate_environment", lambda env: None)
    monkeypatch.setattr(startup, "packaged_heads", lambda: ("head",))
    monkeypatch.setattr(startup, "database_heads", lambda: ("head",))
    monkeypatch.setattr(startup, "check_storage", lambda: None)
    calls = []
    monkeypatch.setattr(startup.os, "execv", lambda executable, args: calls.append((executable, args)))
    assert startup.main() == 0
    assert calls[0][0] == sys.executable
    args = calls[0][1]
    assert args[args.index("--workers") + 1] == "1"
    assert "--no-access-log" in args


def test_release_identity_is_read_from_image_not_copied_render_environment(monkeypatch, tmp_path):
    (tmp_path / "RELEASE_REVISION").write_text("a" * 40 + "\n")
    monkeypatch.setattr(startup, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("RENDER_GIT_COMMIT", "b" * 40)
    monkeypatch.setattr(startup, "validate_environment", lambda env: None)
    monkeypatch.setattr(startup, "packaged_heads", lambda: ("head",))
    monkeypatch.setattr(startup, "database_heads", lambda: ("head",))
    monkeypatch.setattr(startup, "check_storage", lambda: None)
    monkeypatch.setattr(startup.os, "execv", lambda *args: None)
    assert startup.main() == 0
    assert startup.os.environ["RENDER_GIT_COMMIT"] == "a" * 40


def test_invalid_image_revision_blocks_start(monkeypatch, tmp_path):
    (tmp_path / "RELEASE_REVISION").write_text("not-a-commit")
    monkeypatch.setattr(startup, "PROJECT_ROOT", tmp_path)
    with pytest.raises(startup.StartupError, match="INVALID_IMAGE_REVISION"):
        startup.image_revision()
