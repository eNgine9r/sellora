"""Start the Raspberry API only after a read-only schema readiness check."""
from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


class StartupError(RuntimeError):
    """Contains a safe error code, never configuration values."""


def validate_environment(env: Mapping[str, str]) -> None:
    database_url = env.get("DATABASE_URL", "").strip()
    if not database_url:
        raise StartupError("MISSING_DATABASE_URL")
    try:
        parsed = urlsplit(database_url)
        valid = parsed.scheme in {
            "postgresql", "postgresql+psycopg", "postgresql+psycopg2"
        } and bool(parsed.hostname) and bool(parsed.path.strip("/"))
    except ValueError:
        valid = False
    if not valid:
        raise StartupError("INVALID_DATABASE_URL")
    for name in ("SECRET_KEY", "JWT_SECRET"):
        value = env.get(name, "").strip()
        if len(value) < 32 or value.lower().startswith(
            ("change-me", "local-development", "replace-", "example-")
        ):
            raise StartupError(f"UNSAFE_{name}")
    if not re.fullmatch(r"[0-9a-f]{40}", env.get("RENDER_GIT_COMMIT", "")):
        raise StartupError("MISSING_OR_INVALID_RELEASE_REVISION")
    if env.get("META_TOKEN_STORAGE_ENABLED", "").lower() in {"1", "true", "yes", "on"}:
        if not env.get("META_TOKEN_ENCRYPTION_KEY", "").strip():
            raise StartupError("MISSING_META_TOKEN_ENCRYPTION_KEY")
    try:
        port = int(env.get("PORT", "10000"))
    except ValueError:
        raise StartupError("INVALID_PORT") from None
    if not 1024 <= port <= 65535:
        raise StartupError("INVALID_PORT")


def image_revision() -> str:
    revision = (PROJECT_ROOT / "RELEASE_REVISION").read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise StartupError("INVALID_IMAGE_REVISION")
    return revision


def packaged_heads() -> tuple[str, ...]:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    heads = tuple(ScriptDirectory.from_config(config).get_heads())
    if len(heads) != 1:
        raise StartupError("PACKAGED_SCHEMA_MUST_HAVE_ONE_HEAD")
    return heads


def database_heads() -> tuple[str, ...]:
    from alembic.runtime.migration import MigrationContext
    # Reuse the application's Supabase/psycopg connection options.
    from app.database.session import engine

    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            return tuple(MigrationContext.configure(connection).get_current_heads())
    finally:
        engine.dispose()


def ensure_schema_current(expected: tuple[str, ...], actual: tuple[str, ...]) -> None:
    if len(expected) != 1 or set(actual) != set(expected):
        raise StartupError("DATABASE_SCHEMA_MISMATCH")


def check_storage() -> None:
    directory = Path(os.getenv("IMPORT_STORAGE_PATH", "storage/imports"))
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=directory) as probe:
        probe.write(b"sellora-storage-check")


def main() -> int:
    try:
        # Image metadata wins over copied Render runtime environment values.
        os.environ["RENDER_GIT_COMMIT"] = image_revision()
        validate_environment(os.environ)
        os.chdir(PROJECT_ROOT)
        ensure_schema_current(packaged_heads(), database_heads())
        check_storage()
    except StartupError as exc:
        print(f"Raspberry startup blocked: {exc}", file=sys.stderr)
        return 78
    except Exception as exc:
        # DB drivers can include credentials in exception text or tracebacks.
        print(f"Raspberry startup preflight failed: {type(exc).__name__}", file=sys.stderr)
        return 78
    os.execv(sys.executable, [
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--host", "0.0.0.0", "--port", os.getenv("PORT", "10000"),
        "--workers", "1", "--no-access-log",
    ])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
