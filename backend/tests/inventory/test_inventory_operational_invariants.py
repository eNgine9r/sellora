from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransactionType
from app.models.product_variant import ProductVariant
from app.schemas.inventory import InventoryTransactionCreate
from app.services.inventory_service import InventoryServiceError
from tests.test_products_inventory import _inventory_service


def test_low_stock_uses_available_quantity_after_reservation() -> None:
    inventory = Inventory(workspace_id=uuid4(), product_variant_id=uuid4(), stock_quantity=5, reserved_quantity=4, minimum_quantity=1)

    assert inventory.is_low_stock


def test_adjustment_cannot_drop_physical_stock_below_reserved() -> None:
    inventory = Inventory(id=uuid4(), workspace_id=uuid4(), product_variant_id=uuid4(), stock_quantity=5, reserved_quantity=3, minimum_quantity=1)
    service = _inventory_service(inventory)

    with pytest.raises(InventoryServiceError, match="reserved"):
        service.record_transaction(inventory.workspace_id, inventory.id, InventoryTransactionCreate(transaction_type=InventoryTransactionType.ADJUSTMENT, quantity=2, reason="QA8D controlled adjustment"), actor_user_id=uuid4())

    assert inventory.stock_quantity == 5
    assert inventory.reserved_quantity == 3


def test_issue_134_archived_zero_inventory_hidden_but_archived_with_stock_visible() -> None:
    active_workspace = uuid4()
    zero_variant = ProductVariant(id=uuid4(), workspace_id=active_workspace, product_id=uuid4(), sku="ARCH-ZERO")
    zero_variant.deleted_at = datetime.now(UTC)
    zero_inventory = Inventory(id=uuid4(), workspace_id=active_workspace, product_variant_id=zero_variant.id, stock_quantity=0, reserved_quantity=0, minimum_quantity=0, variant=zero_variant)

    stocked_variant = ProductVariant(id=uuid4(), workspace_id=active_workspace, product_id=uuid4(), sku="ARCH-STOCK")
    stocked_variant.deleted_at = datetime.now(UTC)
    stocked_inventory = Inventory(id=uuid4(), workspace_id=active_workspace, product_variant_id=stocked_variant.id, stock_quantity=2, reserved_quantity=0, minimum_quantity=0, variant=stocked_variant)

    active_variant = ProductVariant(id=uuid4(), workspace_id=active_workspace, product_id=uuid4(), sku="ACTIVE")
    active_inventory = Inventory(id=uuid4(), workspace_id=active_workspace, product_variant_id=active_variant.id, stock_quantity=0, reserved_quantity=0, minimum_quantity=0, variant=active_variant)

    visible = [item for item in [zero_inventory, stocked_inventory, active_inventory] if item.variant.deleted_at is None or item.stock_quantity > 0 or item.reserved_quantity > 0]

    assert zero_inventory not in visible
    assert stocked_inventory in visible
    assert active_inventory in visible
