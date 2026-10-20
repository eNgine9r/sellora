"""Regression: SQL bind values must not leak through exception text."""
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.database.session import engine


def test_engine_masks_bound_sql_values():
    assert engine.hide_parameters is True


def test_sqlalchemy_dbapi_error_string_censors_bound_values():
    marker = "private_customer_phone_dont_log_998877"
    error = DBAPIError(
        statement="SELECT * FROM direct_messages WHERE text = :body",
        params={"body": marker},
        orig=ValueError("synthetic SQL error without sensitive fields"),
        hide_parameters=engine.hide_parameters,
    )
    rendered = str(error)
    assert marker not in rendered
    assert "[SQL parameters hidden due to hide_parameters=True]" in rendered
