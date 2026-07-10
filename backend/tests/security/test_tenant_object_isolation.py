from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransactionType
from app.models.lead import Lead
from app.models.order import OrderStatus
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from app.schemas.lead import LeadCreate
from app.schemas.order import OrderCreate, OrderItemCreate
from app.services.lead_service import LeadService, LeadServiceError
from app.services.order_service import OrderService, OrderServiceError


class FakeAuditLogs:
    def __init__(self) -> None:
        self.records = []

    def create(self, **kwargs):
        self.records.append(kwargs)
        return SimpleNamespace(**kwargs)


class FakeLeadRepository:
    def __init__(self, leads: list[Lead]) -> None:
        self.leads = leads
        self.created: list[Lead] = []

    def list_for_workspace(self, workspace_id, search=None, status=None, lead_source_id=None):
        return [lead for lead in self.leads if lead.workspace_id == workspace_id and lead.deleted_at is None]

    def get(self, workspace_id, lead_id):
        return next((lead for lead in self.leads if lead.workspace_id == workspace_id and lead.id == lead_id and lead.deleted_at is None), None)

    def create(self, lead):
        lead.id = lead.id or uuid4()
        self.created.append(lead)
        self.leads.append(lead)
        return lead


class FakeLeadDb:
    def __init__(self, users: dict) -> None:
        self.users = users
        self.committed = False

    def get(self, model, model_id):
        if model is User:
            return self.users.get(model_id)
        return None

    def commit(self) -> None:
        self.committed = True

    def refresh(self, model) -> None:
        pass


class EmptyScopedRepo:
    def get(self, workspace_id, object_id):
        return None


class FakeDb:
    def __init__(self, variant: ProductVariant, customer: Customer) -> None:
        self.variants = {variant.id: variant}
        self.customer = customer

    def get(self, model, model_id):
        if model is ProductVariant:
            return self.variants.get(model_id)
        if model is Customer and model_id == self.customer.id:
            return self.customer
        return None

    def commit(self) -> None:
        pass

    def refresh(self, model) -> None:
        pass


class FakeOrders:
    def create(self, order):
        order.id = order.id or uuid4()
        return order

    def add_item(self, item):
        return item

    def add_status_history(self, history):
        return history

    def next_sequence_for_year(self, workspace_id, year):
        return 1


class FakeInventoryRepo:
    def __init__(self, inventory: Inventory | None) -> None:
        self.inventory = inventory

    def get_by_variant(self, workspace_id, product_variant_id):
        if self.inventory and self.inventory.workspace_id == workspace_id and self.inventory.product_variant_id == product_variant_id:
            return self.inventory
        return None


class FakeInventoryService:
    def record_transaction(self, *args, **kwargs):
        return SimpleNamespace(id=uuid4(), transaction_type=InventoryTransactionType.RESERVE.value)


def _lead_service_with(leads: list[Lead], users: dict | None = None) -> LeadService:
    service = LeadService.__new__(LeadService)
    service.db = FakeLeadDb(users or {})
    service.leads = FakeLeadRepository(leads)
    service.lead_sources = EmptyScopedRepo()
    service.customers = EmptyScopedRepo()
    service.audit_logs = FakeAuditLogs()
    service.campaigns = EmptyScopedRepo()
    return service


def test_lead_list_detail_update_archive_are_workspace_scoped() -> None:
    workspace_a = uuid4()
    workspace_b = uuid4()
    lead_a = Lead(id=uuid4(), workspace_id=workspace_a, name="Synthetic A")
    lead_b = Lead(id=uuid4(), workspace_id=workspace_b, name="Synthetic B")
    service = _lead_service_with([lead_a, lead_b])

    assert service.list(workspace_a) == [lead_a]
    assert service.get(workspace_a, lead_a.id) == lead_a
    assert service.get(workspace_a, lead_b.id) is None
    assert service.update(workspace_a, lead_b.id, payload=SimpleNamespace(model_dump=lambda exclude_unset=True: {"name": "Injected"}), actor_user_id=uuid4()) is None
    assert service.delete(workspace_a, lead_b.id, actor_user_id=uuid4()) is False
    assert lead_b.deleted_at is None
    assert lead_b.name == "Synthetic B"


def test_lead_assignment_rejects_inactive_workspace_membership() -> None:
    workspace_id = uuid4()
    assigned_user_id = uuid4()
    user = SimpleNamespace(
        id=assigned_user_id,
        workspaces=[SimpleNamespace(workspace_id=workspace_id, is_active=False, workspace=SimpleNamespace(is_active=True))],
    )
    service = _lead_service_with([], {assigned_user_id: user})

    with pytest.raises(LeadServiceError, match="Assigned user does not belong"):
        service.create(
            workspace_id,
            LeadCreate(name="Synthetic lead", assigned_user_id=assigned_user_id),
            actor_user_id=uuid4(),
        )

    assert service.db.committed is False
    assert service.leads.created == []


def test_order_creation_rejects_cross_workspace_variant_even_when_variant_id_is_known() -> None:
    workspace_a = uuid4()
    workspace_b = uuid4()
    product_b = Product(id=uuid4(), workspace_id=workspace_b, name="Other product", sku="B")
    variant_b = ProductVariant(id=uuid4(), workspace_id=workspace_b, product_id=product_b.id, sku="B-1", product=product_b)
    customer_a = Customer(id=uuid4(), workspace_id=workspace_a, name="Synthetic customer", phone="000", total_orders=0, total_spent=Decimal("0"))
    inventory_b = Inventory(id=uuid4(), workspace_id=workspace_b, product_variant_id=variant_b.id, stock_quantity=5, reserved_quantity=0, minimum_quantity=1)
    service = OrderService.__new__(OrderService)
    service.db = FakeDb(variant_b, customer_a)
    service.orders = FakeOrders()
    service.inventory = FakeInventoryRepo(inventory_b)
    service.inventory_service = FakeInventoryService()
    service.audit_logs = FakeAuditLogs()
    service.campaigns = EmptyScopedRepo()

    with pytest.raises(OrderServiceError, match="Product variant does not exist in this workspace"):
        service.create(
            workspace_a,
            OrderCreate(
                customer_id=customer_a.id,
                items=[OrderItemCreate(product_variant_id=variant_b.id, quantity=1, unit_price=Decimal("10"), unit_cost=Decimal("5"))],
            ),
            actor_user_id=uuid4(),
        )
