from types import SimpleNamespace
from uuid import uuid4

from app.models.attachment import AttachmentEntityType
from app.models.customer import Customer
from app.models.customer_address import CustomerAddress
from app.models.customer_note import CustomerNote
from app.models.customer_tag import CustomerTag
from app.models.tag import Tag
import pytest

from app.schemas.crm_completion import AttachmentCreate, CustomerAddressCreate, CustomerAddressUpdate, CustomerNoteCreate
from app.services.crm_completion_service import AttachmentService, CustomerCrmService


class FakeDb:
    def __init__(self, customer: Customer) -> None:
        self.customer = customer

    def get(self, model, model_id):
        if model is Customer and model_id == self.customer.id:
            return self.customer
        return SimpleNamespace(id=model_id, workspace_id=self.customer.workspace_id, deleted_at=None)

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


class FakeTagRepo:
    def __init__(self, tag: Tag) -> None:
        self.tag = tag

    def get(self, workspace_id, tag_id):
        if self.tag.workspace_id == workspace_id and self.tag.id == tag_id:
            return self.tag
        return None


class FakeCustomerCrmRepo:
    def __init__(self) -> None:
        self.customer_tags = []
        self.notes = []
        self.addresses = []

    def list_tags(self, workspace_id, customer_id):
        return [item for item in self.customer_tags if item.workspace_id == workspace_id and item.customer_id == customer_id and item.deleted_at is None]

    def get_customer_tag(self, workspace_id, customer_id, tag_id):
        return next((item for item in self.customer_tags if item.workspace_id == workspace_id and item.customer_id == customer_id and item.tag_id == tag_id and item.deleted_at is None), None)

    def add_tag(self, customer_tag):
        customer_tag.id = customer_tag.id or uuid4()
        self.customer_tags.append(customer_tag)
        return customer_tag

    def list_notes(self, workspace_id, customer_id):
        return [item for item in self.notes if item.workspace_id == workspace_id and item.customer_id == customer_id]

    def add_note(self, note):
        note.id = note.id or uuid4()
        self.notes.append(note)
        return note

    def list_addresses(self, workspace_id, customer_id):
        return [item for item in self.addresses if item.workspace_id == workspace_id and item.customer_id == customer_id and item.deleted_at is None]

    def get_address(self, workspace_id, customer_id, address_id):
        return next((item for item in self.addresses if item.workspace_id == workspace_id and item.customer_id == customer_id and item.id == address_id and item.deleted_at is None), None)

    def add_address(self, address):
        address.id = address.id or uuid4()
        self.addresses.append(address)
        return address

    def clear_default_addresses(self, workspace_id, customer_id, except_address_id=None):
        for address in self.list_addresses(workspace_id, customer_id):
            if except_address_id is None or address.id != except_address_id:
                address.is_default = False


class FakeAttachmentRepo:
    def __init__(self) -> None:
        self.attachments = []

    def list_for_workspace(self, workspace_id, entity_type=None, entity_id=None):
        return [item for item in self.attachments if item.workspace_id == workspace_id]

    def create(self, attachment):
        attachment.id = attachment.id or uuid4()
        self.attachments.append(attachment)
        return attachment


def _customer_service() -> tuple[CustomerCrmService, Customer, Tag]:
    customer = Customer(id=uuid4(), workspace_id=uuid4(), name="Customer")
    tag = Tag(id=uuid4(), workspace_id=customer.workspace_id, name="VIP", color="#f59e0b")
    service = CustomerCrmService.__new__(CustomerCrmService)
    service.db = FakeDb(customer)
    service.tags = FakeTagRepo(tag)
    service.customer_crm = FakeCustomerCrmRepo()
    service.audit_logs = FakeAuditLogs()
    return service, customer, tag


def test_customer_can_have_multiple_tags() -> None:
    service, customer, tag = _customer_service()
    second_tag = Tag(id=uuid4(), workspace_id=customer.workspace_id, name="Repeat", color="#22c55e")

    first = service.add_customer_tag(customer.workspace_id, customer.id, tag.id, actor_user_id=uuid4())
    service.tags = FakeTagRepo(second_tag)
    second = service.add_customer_tag(customer.workspace_id, customer.id, second_tag.id, actor_user_id=uuid4())

    assert first.tag_id == tag.id
    assert second.tag_id == second_tag.id
    assert len(service.customer_crm.customer_tags) == 2


def test_customer_may_have_only_one_default_address() -> None:
    service, customer, _tag = _customer_service()

    first = service.add_address(customer.workspace_id, customer.id, CustomerAddressCreate(address_line1="A", is_default=True), actor_user_id=uuid4())
    second = service.add_address(customer.workspace_id, customer.id, CustomerAddressCreate(address_line1="B", is_default=True), actor_user_id=uuid4())

    assert not first.is_default
    assert second.is_default
    assert sum(1 for address in service.customer_crm.addresses if address.is_default) == 1


def test_customer_notes_are_append_only_service_surface() -> None:
    service, customer, _tag = _customer_service()

    note = service.add_note(customer.workspace_id, customer.id, CustomerNoteCreate(note="Called customer"), actor_user_id=uuid4())

    assert note.note == "Called customer"
    assert len(service.list_notes(customer.workspace_id, customer.id)) == 1
    assert not hasattr(service, "update_note")
    assert not hasattr(service, "delete_note")


def test_attachments_support_customer_lead_order_product_and_shipment() -> None:
    customer = Customer(id=uuid4(), workspace_id=uuid4(), name="Customer")
    service = AttachmentService.__new__(AttachmentService)
    service.db = FakeDb(customer)
    service.attachments = FakeAttachmentRepo()
    service.audit_logs = FakeAuditLogs()

    for entity_type in AttachmentEntityType:
        entity_id = customer.id if entity_type == AttachmentEntityType.CUSTOMER else uuid4()
        attachment = service.create(customer.workspace_id, AttachmentCreate(entity_type=entity_type, entity_id=entity_id, file_url=f"https://cdn/{entity_type.value}.pdf"), actor_user_id=uuid4())
        assert attachment.entity_type == entity_type.value

    assert {item.entity_type for item in service.attachments.attachments} == {item.value for item in AttachmentEntityType}


def test_customer_create_schema_accepts_valid_payload() -> None:
    from app.schemas.customer import CustomerCreate

    payload = CustomerCreate.model_validate({"name": "Test Customer", "phone": None, "instagram_username": None})

    assert payload.name == "Test Customer"
    assert payload.phone is None


def test_customer_address_phone_is_normalized() -> None:
    service, customer, _tag = _customer_service()

    address = service.add_address(
        customer.workspace_id,
        customer.id,
        CustomerAddressCreate(address_line1="Відділення №1", phone="067 123 45 67"),
        actor_user_id=uuid4(),
    )

    assert address.phone == "+380671234567"


def test_nova_poshta_city_change_without_warehouse_is_rejected_and_state_unchanged() -> None:
    service, customer, _tag = _customer_service()
    address = service.add_address(
        customer.workspace_id,
        customer.id,
        CustomerAddressCreate(
            address_line1="Відділення №1",
            delivery_provider="NOVA_POSHTA",
            nova_poshta_city_ref="city-old",
            nova_poshta_warehouse_ref="wh-old",
            warehouse_number="1",
        ),
        actor_user_id=uuid4(),
    )

    with pytest.raises(ValueError, match="NOVA_POSHTA_WAREHOUSE_REQUIRED_AFTER_CITY_CHANGE"):
        service.update_address(
            customer.workspace_id,
            customer.id,
            address.id,
            CustomerAddressUpdate(nova_poshta_city_ref="city-new"),
            actor_user_id=uuid4(),
        )

    assert address.nova_poshta_city_ref == "city-old"
    assert address.nova_poshta_warehouse_ref == "wh-old"
    assert address.warehouse_number == "1"
    assert address.address_line1 == "Відділення №1"


def test_nova_poshta_warehouse_ref_without_description_is_rejected() -> None:
    service, customer, _tag = _customer_service()
    address = service.add_address(
        customer.workspace_id,
        customer.id,
        CustomerAddressCreate(
            address_line1="Відділення №1",
            delivery_provider="NOVA_POSHTA",
            nova_poshta_city_ref="city-old",
            nova_poshta_warehouse_ref="wh-old",
        ),
        actor_user_id=uuid4(),
    )

    with pytest.raises(ValueError, match="NOVA_POSHTA_WAREHOUSE_DESCRIPTION_REQUIRED"):
        service.update_address(
            customer.workspace_id,
            customer.id,
            address.id,
            CustomerAddressUpdate(nova_poshta_warehouse_ref="wh-new"),
            actor_user_id=uuid4(),
        )

    assert address.nova_poshta_warehouse_ref == "wh-old"
    assert address.address_line1 == "Відділення №1"


def test_nova_poshta_complete_city_and_warehouse_replacement_succeeds() -> None:
    service, customer, _tag = _customer_service()
    address = service.add_address(
        customer.workspace_id,
        customer.id,
        CustomerAddressCreate(
            address_line1="Відділення №1",
            delivery_provider="NOVA_POSHTA",
            nova_poshta_city_ref="city-old",
            nova_poshta_warehouse_ref="wh-old",
            warehouse_number="1",
        ),
        actor_user_id=uuid4(),
    )

    updated = service.update_address(
        customer.workspace_id,
        customer.id,
        address.id,
        CustomerAddressUpdate(
            nova_poshta_city_ref="city-new",
            nova_poshta_warehouse_ref="wh-new",
            address_line1="Відділення №2",
            warehouse_number="2",
        ),
        actor_user_id=uuid4(),
    )

    assert updated is address
    assert address.nova_poshta_city_ref == "city-new"
    assert address.nova_poshta_warehouse_ref == "wh-new"
    assert address.warehouse_number == "2"
    assert address.address_line1 == "Відділення №2"


def test_generic_non_nova_poshta_address_city_update_remains_compatible() -> None:
    service, customer, _tag = _customer_service()
    address = service.add_address(
        customer.workspace_id,
        customer.id,
        CustomerAddressCreate(address_line1="Generic address", city="Київ", delivery_provider="OTHER"),
        actor_user_id=uuid4(),
    )

    updated = service.update_address(
        customer.workspace_id,
        customer.id,
        address.id,
        CustomerAddressUpdate(city="Львів"),
        actor_user_id=uuid4(),
    )

    assert updated is address
    assert address.city == "Львів"
    assert address.address_line1 == "Generic address"
