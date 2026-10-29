import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

path = Path(__file__).resolve().parents[1] / "scripts/direct_client_conflict_e2e.py"
spec = importlib.util.spec_from_file_location("direct_conflict_fixture", path)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def environment():
    return {"SELLORA_DIRECT_CONFLICT_E2E": "YES",
            "DATABASE_URL": f"postgresql+psycopg://synthetic:synthetic@127.0.0.1/{fixture.DATABASE_NAME}",
            **{name: "false" for name in fixture.DISABLED_FEATURES}}


def test_exact_opt_in_local_postgres_target_is_accepted_without_connecting():
    assert fixture.require_disposable_target(environment()).database == fixture.DATABASE_NAME


@pytest.mark.parametrize("changes", [
    {"SELLORA_DIRECT_CONFLICT_E2E": ""},
    {"DATABASE_URL": "sqlite+pysqlite:///:memory:"},
    {"DATABASE_URL": f"postgresql+psycopg://synthetic@remote.invalid/{fixture.DATABASE_NAME}"},
    {"DATABASE_URL": "postgresql+psycopg://synthetic@127.0.0.1/sellora"},
    {"DATABASE_URL": f"postgresql+psycopg://synthetic@127.0.0.1/{fixture.DATABASE_NAME}?host=remote.invalid"},
    *[{name: "true"} for name in fixture.DISABLED_FEATURES],
])
def test_seed_and_verification_refuse_unsafe_targets_before_any_database_connection(changes):
    with pytest.raises(RuntimeError):
        fixture.require_disposable_target(environment() | changes)


def test_nonempty_database_is_refused_before_creating_any_synthetic_records():
    db = SimpleNamespace(execute=lambda _: None, scalar=lambda _: 1)
    with pytest.raises(RuntimeError, match="no application data"):
        fixture.seed(db)
