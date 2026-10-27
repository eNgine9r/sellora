from collections.abc import Generator
from typing import Any
import time

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.runtime_health import record_db_operation


def engine_connect_args(database_url: str) -> dict[str, Any]:
    """Return driver-specific SQLAlchemy connect args.

    Supabase's PostgreSQL pooler can reuse pooled connections in a way that
    conflicts with psycopg's automatically prepared statements. Disabling
    psycopg prepared statements avoids DuplicatePreparedStatement startup
    crashes while keeping the deployment architecture unchanged.
    """
    if not database_url.startswith(("postgresql://", "postgresql+psycopg://", "postgresql+psycopg2://")):
        return {}
    args: dict[str, Any] = {
        "connect_timeout": 10, "keepalives": 1,
        "keepalives_idle": 30, "keepalives_interval": 10,
        "keepalives_count": 3, "tcp_user_timeout": 15000,
        "options": "-c statement_timeout=15000 -c lock_timeout=5000",
    }
    if database_url.startswith("postgresql+psycopg://"):
        args["prepare_threshold"] = None
    return args


def set_transaction_schema(connection: Any) -> None:
    """Resolve public application tables for each PostgreSQL transaction.

    A transaction pooler may assign a different server connection each time.
    A connection- or role-wide search_path is not reliable under transaction
    pooling; SET LOCAL ends automatically on COMMIT or ROLLBACK. pg_catalog is
    searched first to avoid untrusted function shadowing.
    """
    connection.exec_driver_sql(
        "SET LOCAL search_path TO pg_catalog, public, extensions"
    )


def install_postgres_transaction_schema(target_engine: Any) -> None:
    """Install once on the app's PostgreSQL engine, not on SQLite test engines."""
    if target_engine.dialect.name == "postgresql":
        event.listen(target_engine, "begin", set_transaction_schema)


DB_POOL_SIZE = 5
DB_POOL_MAX_OVERFLOW = 5
DB_POOL_WAIT_SECONDS = 5

settings = get_settings()
# Never interpolate customer message text, phone numbers or token-like bind values
# into SQLAlchemy exception/log messages. Keep SQL statement metadata.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    hide_parameters=True,
    connect_args=engine_connect_args(settings.database_url),
    **({"pool_size": DB_POOL_SIZE, "max_overflow": DB_POOL_MAX_OVERFLOW, "pool_timeout": DB_POOL_WAIT_SECONDS, "pool_recycle": 300}
       if settings.database_url.startswith("postgresql") else {}),
)
# Applied to all transactions, including direct SQLAlchemy Connection usage.
# No persistent ALTER ROLE/ALTER DATABASE, no cross-tenant global state.
install_postgres_transaction_schema(engine)


class InstrumentedSession(Session):
    def execute(self, *args, **kwargs):
        started = time.monotonic()
        try:
            return super().execute(*args, **kwargs)
        finally:
            # Includes connection acquisition and query time; never logs SQL or binds.
            record_db_operation(time.monotonic() - started)


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=InstrumentedSession)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
