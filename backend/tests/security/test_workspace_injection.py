from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.schemas.product import ProductCreate, ProductUpdate, ProductVariantCreate
from app.services.product_service import ProductService, ProductServiceError


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, _model) -> None:
        return None


class FakeAuditLogs:
    def __init__(self) -> None:
        self.records = []

    def create(self, **kwargs):
        self.records.append(kwargs)
        return SimpleNamespace(**kwargs)


class FakeProductRepository:
    def __init__(self, products: list[Product]) -> None:
        self.products = products
        self.created: list[Product] = []

    def get(self, workspace_id, product_id):
        return next((product for product in self.products if product.workspace_id == workspace_id and product.id == product_id and product.deleted_at is None), None)

    def create(self, product: Product) -> Product:
        product.id = product.id or uuid4()
        self.products.append(product)
        self.created.append(product)
        return product

    def create_image(self, image):
        return image


class FakeVariantRepository:
    def __init__(self) -> None:
        self.created: list[ProductVariant] = []

    def find_by_identity(self, product_id, color, size):
        return None

    def find_by_sku(self, workspace_id, sku):
        return None

    def create(self, variant: ProductVariant) -> ProductVariant:
        variant.id = variant.id or uuid4()
        self.created.append(variant)
        return variant


class FakeInventoryRepository:
    def __init__(self) -> None:
        self.created = []

    def create(self, inventory):
        self.created.append(inventory)
        return inventory


def _product_service(products: list[Product]) -> ProductService:
    service = ProductService.__new__(ProductService)
    service.db = FakeDb()
    service.products = FakeProductRepository(products)
    service.variants = FakeVariantRepository()
    service.inventory = FakeInventoryRepository()
    service.audit_logs = FakeAuditLogs()
    return service


def test_create_payload_workspace_injection_cannot_override_server_workspace_context() -> None:
    workspace_a = uuid4()
    workspace_b = uuid4()
    service = _product_service([])
    payload = ProductCreate.model_validate({"name": "Synthetic injected entity", "sku": "SEC-7E1-CREATE", "workspace_id": workspace_b})

    created = service.create_product(workspace_a, payload, actor_user_id=uuid4())

    assert created.workspace_id == workspace_a
    assert all(product.workspace_id != workspace_b for product in service.products.created)
    assert service.db.commits == 1
    assert service.audit_logs.records[0]["workspace_id"] == workspace_a


def test_update_payload_workspace_injection_cannot_move_existing_object_between_workspaces() -> None:
    workspace_a = uuid4()
    workspace_b = uuid4()
    product_a = Product(id=uuid4(), workspace_id=workspace_a, name="Synthetic A", sku="SEC-7E1-A")
    product_b = Product(id=uuid4(), workspace_id=workspace_b, name="Synthetic B", sku="SEC-7E1-B")
    service = _product_service([product_a, product_b])
    payload = ProductUpdate.model_validate({"name": "Attempted tenant move", "workspace_id": workspace_b, "tenant_id": workspace_b})

    updated = service.update_product(workspace_a, product_a.id, payload, actor_user_id=uuid4())

    assert updated is product_a
    assert product_a.workspace_id == workspace_a
    assert product_a.name == "Attempted tenant move"
    assert product_b.workspace_id == workspace_b
    assert product_b.name == "Synthetic B"
    assert service.db.commits == 1
    assert service.audit_logs.records[0]["workspace_id"] == workspace_a


def test_nested_cross_workspace_reference_injection_is_rejected_without_side_effects() -> None:
    workspace_a = uuid4()
    workspace_b = uuid4()
    product_b = Product(id=uuid4(), workspace_id=workspace_b, name="Synthetic foreign product", sku="SEC-7E1-FOREIGN")
    service = _product_service([product_b])
    payload = ProductVariantCreate.model_validate({
        "product_id": product_b.id,
        "sku": "SEC-7E1-NESTED",
        "initial_stock_quantity": 3,
        "minimum_quantity": 1,
        "workspace_id": workspace_b,
        "owner_workspace_id": workspace_b,
    })

    with pytest.raises(ProductServiceError, match="Product does not exist in this workspace"):
        service.create_variant(workspace_a, payload, actor_user_id=uuid4())

    assert service.variants.created == []
    assert service.inventory.created == []
    assert service.audit_logs.records == []
    assert service.db.commits == 0
