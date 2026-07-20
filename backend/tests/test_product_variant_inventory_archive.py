from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.inventory import Inventory
from app.models.product_variant import ProductVariant
from app.services.product_service import ProductService, ProductServiceError


class FakeDB:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


class FakeVariantRepository:
    def __init__(self, variant: ProductVariant) -> None:
        self.variant = variant

    def get(self, workspace_id, variant_id):
        if self.variant.workspace_id != workspace_id or self.variant.id != variant_id or self.variant.deleted_at is not None:
            return None
        return self.variant

    def soft_delete(self, variant, actor_user_id):
        from datetime import UTC, datetime

        variant.deleted_at = datetime.now(UTC)
        variant.deleted_by = actor_user_id


class FakeInventoryRepository:
    def __init__(self, inventory: Inventory | None) -> None:
        self.inventory = inventory
        self.lock_calls = []

    def get_by_variant_for_update(self, workspace_id, variant_id):
        self.lock_calls.append((workspace_id, variant_id))
        if self.inventory is None:
            return None
        if self.inventory.workspace_id != workspace_id or self.inventory.product_variant_id != variant_id or self.inventory.deleted_at is not None:
            return None
        return self.inventory


class FakeAuditLogRepository:
    def __init__(self) -> None:
        self.entries = []

    def create(self, **kwargs):
        self.entries.append(kwargs)


def build_service(variant: ProductVariant, inventory: Inventory | None):
    service = ProductService.__new__(ProductService)
    service.db = FakeDB()
    service.variants = FakeVariantRepository(variant)
    service.inventory = FakeInventoryRepository(inventory)
    service.audit_logs = FakeAuditLogRepository()
    return service


def make_variant(workspace_id, variant_id):
    return ProductVariant(
        id=variant_id,
        workspace_id=workspace_id,
        product_id=uuid4(),
        sku="ARCHIVE-TEST",
        color="black",
        size="M",
        price=Decimal("100.00"),
        is_active=True,
    )


def make_inventory(workspace_id, variant_id, reserved_quantity=0):
    return Inventory(
        id=uuid4(),
        workspace_id=workspace_id,
        product_variant_id=variant_id,
        stock_quantity=0,
        reserved_quantity=reserved_quantity,
        incoming_quantity=0,
        minimum_quantity=0,
    )


def test_archiving_variant_soft_deletes_inventory_in_same_transaction_and_keeps_audit_entries():
    workspace_id = uuid4()
    actor_user_id = uuid4()
    variant_id = uuid4()
    variant = make_variant(workspace_id, variant_id)
    inventory = make_inventory(workspace_id, variant_id)
    service = build_service(variant, inventory)

    assert service.delete_variant(workspace_id, variant_id, actor_user_id) is True

    assert variant.deleted_at is not None
    assert variant.deleted_by == actor_user_id
    assert inventory.deleted_at is not None
    assert inventory.deleted_by == actor_user_id
    assert service.db.commits == 1
    assert service.inventory.lock_calls == [(workspace_id, variant_id)]
    assert {entry["action"] for entry in service.audit_logs.entries} == {
        "PRODUCT_VARIANT_ARCHIVE",
        "INVENTORY_ARCHIVE_WITH_VARIANT",
    }


def test_archiving_variant_with_reserved_inventory_is_rejected_without_partial_changes():
    workspace_id = uuid4()
    actor_user_id = uuid4()
    variant_id = uuid4()
    variant = make_variant(workspace_id, variant_id)
    inventory = make_inventory(workspace_id, variant_id, reserved_quantity=1)
    service = build_service(variant, inventory)

    with pytest.raises(ProductServiceError, match="reserved inventory"):
        service.delete_variant(workspace_id, variant_id, actor_user_id)

    assert variant.deleted_at is None
    assert inventory.deleted_at is None
    assert service.db.commits == 0
    assert service.audit_logs.entries == []


def test_variant_archive_cannot_cross_workspace_boundary():
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    variant_id = uuid4()
    variant = make_variant(workspace_id, variant_id)
    inventory = make_inventory(workspace_id, variant_id)
    service = build_service(variant, inventory)

    assert service.delete_variant(other_workspace_id, variant_id, uuid4()) is False

    assert variant.deleted_at is None
    assert inventory.deleted_at is None
    assert service.db.commits == 0
    assert service.inventory.lock_calls == []
