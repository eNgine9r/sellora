from pathlib import Path


MIGRATIONS = (
    Path("alembic/versions/202607080020_secure_public_tables_rls.py"),
    Path("alembic/versions/202607150022_nova_poshta_durable_operations.py"),
)


def test_supabase_role_revokes_are_safe_on_plain_postgres() -> None:
    for migration in MIGRATIONS:
        source = migration.read_text()

        assert "SELECT 1 FROM pg_roles WHERE rolname" in source
        assert 'for role_name in ("anon", "authenticated")' in source
        assert "FROM anon, authenticated" not in source
