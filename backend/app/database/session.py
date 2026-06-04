from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def engine_connect_args(database_url: str) -> dict[str, Any]:
    """Return driver-specific SQLAlchemy connect args.

    Supabase's PostgreSQL pooler can reuse pooled connections in a way that
    conflicts with psycopg's automatically prepared statements. Disabling
    psycopg prepared statements avoids DuplicatePreparedStatement startup
    crashes while keeping the deployment architecture unchanged.
    """
    if database_url.startswith("postgresql+psycopg://"):
        return {"prepare_threshold": None}
    return {}


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=engine_connect_args(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
