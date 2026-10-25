"""Protect runtime auth under restricted PostgreSQL search_path.

The runtime PostgreSQL role may run individual transactions with search_path
set to the empty string. SQLAlchemy model queries are schema-qualified, but
hand-written authorization SQL must explicitly reference public tables.
"""
from pathlib import Path
import re

import pytest

APP = Path(__file__).resolve().parents[2] / "app"


@pytest.mark.parametrize(
    ("module", "table"),
    [
        ("dependencies/auth.py", "auth_sessions"),
        ("auth/session_service.py", "auth_sessions"),
        ("auth/login_throttle.py", "auth_login_attempts"),
    ],
)
def test_critical_auth_sql_uses_public_schema(module: str, table: str) -> None:
    source = (APP / module).read_text()
    statements = re.findall(
        rf"(?i)\b(?:FROM|INTO|UPDATE|JOIN)\s+((?:public\.)?{table})\b",
        source,
    )
    assert statements, f"No SQL statements found for {table}"
    assert all(name.lower() == f"public.{table}" for name in statements)
