from pathlib import Path


def test_consolidation_migration_is_forward_only_and_drops_duplicate_table() -> None:
    migration = Path("alembic/versions/202607180026_consolidate_order_fulfillment_journal.py").read_text()
    assert 'down_revision: str | None = "202607180025"' in migration
    assert 'op.drop_table("order_fulfillment_operations")' in migration
    assert 'uq_order_fulfillments_one_active_per_order' in migration
    assert 'FULFILLMENT_JOURNAL_CONFLICT' in migration
