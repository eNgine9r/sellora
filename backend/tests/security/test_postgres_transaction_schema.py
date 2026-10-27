"""Guard against transaction-pooling search_path regression (Issue #333)."""
from unittest.mock import Mock, patch

from sqlalchemy import create_engine, text

from app.database.session import (
    engine_connect_args,
    install_postgres_transaction_schema,
    set_transaction_schema,
)


def test_begin_event_installed_only_for_postgres() -> None:
    pg = Mock()
    pg.dialect.name = "postgresql"
    with patch("app.database.session.event.listen") as listener:
        install_postgres_transaction_schema(pg)
    listener.assert_called_once_with(pg, "begin", set_transaction_schema)


def test_transaction_schema_statement_is_local_and_pg_catalog_first() -> None:
    connection = Mock()
    set_transaction_schema(connection)
    connection.exec_driver_sql.assert_called_once_with(
        "SET LOCAL search_path TO pg_catalog, public, extensions"
    )


def test_non_postgres_sqlite_not_affected() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with patch("app.database.session.event.listen") as listener:
        install_postgres_transaction_schema(engine)
    listener.assert_not_called()
    with engine.begin() as conn:
        assert conn.scalar(text("SELECT 123")) == 123
    engine.dispose()


def test_keep_pgbouncer_prepared_statement_disabled() -> None:
    args = engine_connect_args("postgresql+psycopg://u:p@localhost:5432/db")
    assert args["prepare_threshold"] is None
    assert args["options"].startswith("-c statement_timeout=")
