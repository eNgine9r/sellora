from pathlib import Path


MIGRATION = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "202607220035_zero_excluded_order_profit.py"
)


def test_migration_targets_only_financially_excluded_orders():
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "202607220035"' in source
    assert 'down_revision: str | None = "202607220034"' in source
    assert "SET net_profit = 0" in source
    assert "status IN ('CANCELLED', 'RETURNED')" in source
    assert "payment_status = 'REFUNDED'" in source
    assert "WHERE net_profit <> 0" in source


def test_downgrade_does_not_invent_legacy_financial_values():
    source = MIGRATION.read_text(encoding="utf-8")

    downgrade = source.split("def downgrade() -> None:", 1)[1]
    assert "UPDATE orders" not in downgrade
