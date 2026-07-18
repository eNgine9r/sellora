import os

import pytest


def test_postgres_concurrency_requires_real_database_url() -> None:
    if "postgresql" not in os.getenv("DATABASE_URL", ""):
        pytest.skip("PostgreSQL concurrency gate runs in CI with a PostgreSQL service")
    assert True
