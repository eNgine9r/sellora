from types import SimpleNamespace
from uuid import uuid4

from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransactionType
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.schemas.inventory import InventoryTransactionCreate
from app.schemas.product import ProductCreate, ProductVariantCreate
from app.services.inventory_service import InventoryService, InventoryServiceError
from app.services.product_service import ProductService, ProductServiceError


class FakeDb:
    def commit(self) -> None:
        pass

    def refresh(self, model) -> None:
        pass


class FakeAuditLogs:
    def __init__(self) -> None:
        self.records = []

    def create(self, **kwargs):
        self.records.append(kwargs)
        return SimpleNamespace(**kwargs)


class FakeProducts:
    def __init__(self, product: Product | None = None) -> None:
        self.product = product
        self.images = []

    def get(self, workspace_id, product_id):
        if self.product and self.product.workspace_id == workspace_id and self.product.id == product_id:
            return self.product
        return None

    def create(self, product):
        product.id = product.id or uuid4()
        self.product = product
        return product

    def create_image(self, image):
        image.id = image.id or uuid4()
        self.images.append(image)
        return image


class FakeVariants:
    def __init__(self) -> None:
        self.variants = {}

    def find_by_identity(self, product_id, color, size):
        for variant in self.variants.values():
            if variant.product_id == product_id and variant.color == color and variant.size == size:
                return variant
        return None

    def create(self, variant):
        variant.id = variant.id or uuid4()
        self.variants[variant.id] = variant
        return variant

    def get(self, workspace_id, variant_id):
        variant = self.variants.get(variant_id)
        if variant and variant.workspace_id == workspace_id:
            return variant
        return None


class FakeInventory:
    def __init__(self, inventory: Inventory | None = None) -> None:
        self.inventory = inventory

    def create(self, inventory):
        inventory.id = inventory.id or uuid4()
        self.inventory = inventory
        return inventory

    def get(self, workspace_id, inventory_id):
        if self.inventory and self.inventory.workspace_id == workspace_id and self.inventory.id == inventory_id:
            return self.inventory
        return None


class FakeTransactions:
    def __init__(self) -> None:
        self.transactions = []

    def create(self, transaction):
        transaction.id = transaction.id or uuid4()
        self.transactions.append(transaction)
        return transaction


def _product_service(product: Product | None = None) -> ProductService:
    service = ProductService.__new__(ProductService)
    service.db = FakeDb()
    service.products = FakeProducts(product)
    service.variants = FakeVariants()
    service.inventory = FakeInventory()
    service.audit_logs = FakeAuditLogs()
    return service


def _inventory_service(inventory: Inventory) -> InventoryService:
    service = InventoryService.__new__(InventoryService)
    service.db = FakeDb()
    service.inventory = FakeInventory(inventory)
    service.transactions = FakeTransactions()
    service.audit_logs = FakeAuditLogs()
    return service


def test_product_creation_supports_sku_and_images() -> None:
    workspace_id = uuid4()
    service = _product_service()

    product = service.create_product(
        workspace_id,
        ProductCreate(name="Dress", sku="DR-001", images=[{"image_url": "https://cdn.example/dress.jpg", "is_primary": True}]),
        actor_user_id=uuid4(),
    )

    assert product.sku == "DR-001"
    assert service.products.images[0].image_url == "https://cdn.example/dress.jpg"
    assert service.audit_logs.records[-1]["action"] == "CREATE"


def test_product_variant_uniqueness_and_inventory_auto_creation() -> None:
    workspace_id = uuid4()
    product = Product(id=uuid4(), workspace_id=workspace_id, name="Dress", sku="DR-001")
    service = _product_service(product)
    payload = ProductVariantCreate(product_id=product.id, sku="DR-001-RED-S", color="Red", size="S", initial_stock_quantity=5, minimum_quantity=2)

    variant = service.create_variant(workspace_id, payload, actor_user_id=uuid4())

    assert variant.sku == "DR-001-RED-S"
    assert service.inventory.inventory.product_variant_id == variant.id
    assert service.inventory.inventory.stock_quantity == 5
    assert service.inventory.inventory.minimum_quantity == 2

    try:
        service.create_variant(workspace_id, payload, actor_user_id=uuid4())
    except ProductServiceError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("duplicate variant should fail")


def test_low_stock_detection_uses_minimum_quantity() -> None:
    inventory = Inventory(workspace_id=uuid4(), product_variant_id=uuid4(), stock_quantity=2, reserved_quantity=0, minimum_quantity=2)

    assert inventory.is_low_stock


def test_inventory_stock_in_transaction_is_logged() -> None:
    inventory = Inventory(id=uuid4(), workspace_id=uuid4(), product_variant_id=uuid4(), stock_quantity=2, reserved_quantity=0, minimum_quantity=1)
    service = _inventory_service(inventory)

    transaction = service.record_transaction(
        inventory.workspace_id,
        inventory.id,
        InventoryTransactionCreate(transaction_type=InventoryTransactionType.STOCK_IN, quantity=3, reason="Restock"),
        actor_user_id=uuid4(),
    )

    assert transaction.previous_stock_quantity == 2
    assert transaction.new_stock_quantity == 5
    assert inventory.stock_quantity == 5
    assert service.audit_logs.records[-1]["action"] == InventoryTransactionType.STOCK_IN.value


def test_inventory_reserve_cannot_exceed_available_stock() -> None:
    inventory = Inventory(id=uuid4(), workspace_id=uuid4(), product_variant_id=uuid4(), stock_quantity=2, reserved_quantity=0, minimum_quantity=1)
    service = _inventory_service(inventory)

    try:
        service.record_transaction(
            inventory.workspace_id,
            inventory.id,
            InventoryTransactionCreate(transaction_type=InventoryTransactionType.RESERVE, quantity=3),
            actor_user_id=uuid4(),
        )
    except InventoryServiceError as exc:
        assert "reserve more than available" in str(exc)
    else:
        raise AssertionError("over-reserving should fail")


def test_inventory_workspace_isolation_returns_none_for_other_workspace() -> None:
    inventory = Inventory(id=uuid4(), workspace_id=uuid4(), product_variant_id=uuid4(), stock_quantity=1, reserved_quantity=0, minimum_quantity=1)
    service = _inventory_service(inventory)

    assert service.get_inventory(uuid4(), inventory.id) is None


def test_product_create_schema_accepts_minimal_payload() -> None:
    from app.schemas.product import ProductCreate

    payload = ProductCreate.model_validate({"name": "Minimal product"})

    assert payload.name == "Minimal product"
    assert payload.sku is None
    assert payload.images == []


def test_product_create_schema_rejects_missing_name() -> None:
    from pydantic import ValidationError
    from app.schemas.product import ProductCreate

    try:
        ProductCreate.model_validate({"sku": "SKU-1"})
    except ValidationError as exc:
        assert any(error["loc"] == ("name",) for error in exc.errors())
    else:
        raise AssertionError("ProductCreate should require name")


def test_product_variant_create_schema_accepts_valid_payload() -> None:
    from uuid import uuid4
    from app.schemas.product import ProductVariantCreate

    product_id = uuid4()
    payload = ProductVariantCreate.model_validate({"product_id": product_id, "sku": "VAR-1", "price": 100, "initial_stock_quantity": 2})

    assert payload.product_id == product_id
    assert payload.sku == "VAR-1"
