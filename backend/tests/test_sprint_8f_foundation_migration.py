from pathlib import Path

from app.models.customer_address import CustomerAddress

MIGRATION = Path("alembic/versions/202607160023_sprint_8f_foundation.py")


def test_migration_repairs_duplicate_defaults_before_partial_index() -> None:
    source = MIGRATION.read_text()
    repair_position = source.index("WITH ranked_defaults AS")
    index_position = source.index("uq_customer_addresses_one_active_default")

    assert repair_position < index_position
    assert "row_number() OVER" in source
    assert "PARTITION BY workspace_id, customer_id" in source
    assert "SET is_default = false" in source


def test_customer_address_model_contains_matching_partial_default_index() -> None:
    indexes = {index.name: index for index in CustomerAddress.__table__.indexes}
    index = indexes["uq_customer_addresses_one_active_default"]

    assert [column.name for column in index.columns] == ["workspace_id", "customer_id"]
    assert index.unique is True
    assert str(index.dialect_options["postgresql"]["where"]) == "is_default = true AND deleted_at IS NULL"
