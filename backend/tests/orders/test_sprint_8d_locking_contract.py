from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_inventory_mutations_use_postgresql_row_locks() -> None:
    repository = read("app/repositories/inventory_repository.py")
    service = read("app/services/inventory_service.py")

    assert "def get_for_update" in repository
    assert ".with_for_update()" in repository
    assert "populate_existing=True" in repository
    assert "_get_inventory_for_update" in service
    assert "stock_quantity < inventory.reserved_quantity" in service


def test_order_mutations_lock_order_and_allow_outer_transaction_control() -> None:
    repository = read("app/repositories/order_repository.py")
    service = read("app/services/order_service.py")

    assert "def get_for_update" in repository
    assert ".with_for_update()" in repository
    assert "commit: bool = True" in service
    assert "self.db.flush()" in service
    assert "sorted(order.items" in service


def test_shipment_order_inventory_side_effects_share_one_commit_boundary() -> None:
    repository = read("app/repositories/shipment_repository.py")
    service = read("app/services/shipment_service.py")

    assert "def get_for_update" in repository
    assert ".with_for_update()" in repository
    assert "commit=False" in service
    assert "self.order_service.change_status" in service
    assert "self.db.commit()" in service
    assert "IntegrityError" in service
