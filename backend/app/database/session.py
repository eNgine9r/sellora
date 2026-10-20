from collections.abc import Generator
from typing import Any
import time

from sqlalchemy import create_engine
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


settings = get_settings()
# Never interpolate customer message text, phone numbers or token-like bind values
# into SQLAlchemy exception/log messages. Keep SQL statement metadata.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    hide_parameters=True,
    connect_args=engine_connect_args(settings.database_url),
    **({"pool_size": 5, "max_overflow": 5, "pool_timeout": 5, "pool_recycle": 300}
       if settings.database_url.startswith("postgresql") else {}),
)
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
