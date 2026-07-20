from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.models.ai_direct import DirectConversation, DirectMessage
from app.models.customer import CustomerLifecycleStatus, CustomerProfileStatus, CustomerSource
from app.schemas.direct_customer_automation import DirectCustomerCompleteRequest
from app.services.direct_customer_automation_service import DirectCustomerAutomationService


class FakeDb:
    def commit(self):
        pass

    def flush(self):
        pass

    def refresh(self, _model):
        pass


class FakeConversationRepository:
    def __init__(self, conversation):
        self.conversation = conversation

    def get(self, workspace_id, conversation_id):
        if self.conversation.workspace_id == workspace_id and self.conversation.id == conversation_id:
            return self.conversation
        return None


class FakeMessageRepository:
    def __init__(self, message):
        self.message = message

    def latest_analyzable(self, workspace_id, conversation_id):
        if self.message.workspace_id == workspace_id and self.message.conversation_id == conversation_id:
            return self.message
        return None


class FakeCustomerRepository:
    def __init__(self):
        self.customers = []

    def get(self, workspace_id, customer_id):
        return next((item for item in self.customers if item.workspace_id == workspace_id and item.id == customer_id), None)

    def find_by_instagram_identity(self, workspace_id, instagram_scoped_id=None, instagram_username=None):
        normalized = (instagram_username or "").lstrip("@").lower()
        return next(
            (
                item
                for item in self.customers
                if item.workspace_id == workspace_id
                and (
                    (instagram_scoped_id and item.instagram_scoped_id == instagram_scoped_id)
                    or (normalized and (item.instagram_username or "").lower() == normalized)
                )
            ),
            None,
        )

    def create(self, customer):
        now = datetime.now(UTC)
        customer.id = customer.id or uuid4()
        customer.total_orders = customer.total_orders or 0
        customer.total_spent = customer.total_spent or Decimal("0")
        customer.created_at = now
        customer.updated_at = now
        customer.deleted_at = None
        self.customers.append(customer)
        return customer


class FakeCustomerCrm:
    def __init__(self):
        self.addresses = []

    def list_addresses(self, workspace_id, customer_id):
        return [item for item in self.addresses if item.workspace_id == workspace_id and item.customer_id == customer_id]

    def add_address(self, workspace_id, customer_id, payload, actor_user_id, commit=False):
        address = SimpleNamespace(
            id=uuid4(),
            workspace_id=workspace_id,
            customer_id=customer_id,
            **payload.model_dump(),
        )
        self.addresses.append(address)
        return address

    def update_address(self, workspace_id, customer_id, address_id, payload, actor_user_id, commit=False):
        address = next(item for item in self.addresses if item.id == address_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(address, key, value)
        return address


class FakeAuditLogs:
    def __init__(self):
        self.records = []

    def create(self, **kwargs):
        self.records.append(kwargs)
        return SimpleNamespace(**kwargs)


def make_service(message_text="Хочу замовити цей годинник"):
    workspace_id = uuid4()
    conversation = DirectConversation(
        id=uuid4(),
        workspace_id=workspace_id,
        channel="INSTAGRAM",
        participant_scoped_id="igs-user-1",
        participant_username="buyer_one",
        participant_display_name="Марія",
        unread_count=1,
        status="OPEN",
        priority="NORMAL",
        ai_processing_status="NOT_REQUESTED",
    )
    message = DirectMessage(
        id=uuid4(),
        workspace_id=workspace_id,
        conversation_id=conversation.id,
        direction="INBOUND",
        sender_type="CUSTOMER",
        message_type="TEXT",
        text=message_text,
        received_at=datetime.now(UTC),
        processing_status="RECEIVED",
        is_synthetic=False,
    )
    service = DirectCustomerAutomationService.__new__(DirectCustomerAutomationService)
    service.db = FakeDb()
    service.conversations = FakeConversationRepository(conversation)
    service.messages = FakeMessageRepository(message)
    service.customers = FakeCustomerRepository()
    service.customer_crm = FakeCustomerCrm()
    service.audit_logs = FakeAuditLogs()
    return service, conversation, workspace_id


def test_order_intent_creates_one_workspace_scoped_prospect_and_links_conversation():
    service, conversation, workspace_id = make_service()

    first = service.ensure_from_inbound_order_intent(workspace_id, conversation.id, "Хочу замовити")
    second = service.ensure_from_inbound_order_intent(workspace_id, conversation.id, "Оформіть замовлення")

    assert first is not None
    assert second is not None
    assert len(service.customers.customers) == 1
    assert conversation.linked_customer_id == first.customer.id == second.customer.id
    customer = service.customers.customers[0]
    assert customer.source == CustomerSource.INSTAGRAM_DIRECT.value
    assert customer.lifecycle_status == CustomerLifecycleStatus.PROSPECT.value
    assert customer.profile_status == CustomerProfileStatus.INCOMPLETE.value
    assert customer.instagram_scoped_id == "igs-user-1"
    assert customer.instagram_username == "buyer_one"
    assert customer.workspace_id == workspace_id


def test_non_order_message_does_not_create_customer():
    service, conversation, workspace_id = make_service("Дякую")

    state = service.ensure_from_inbound_order_intent(workspace_id, conversation.id, "Дякую")

    assert state is None
    assert service.customers.customers == []
    assert conversation.linked_customer_id is None


def test_customer_completion_after_linked_order_saves_delivery_profile():
    service, conversation, workspace_id = make_service()
    prospect = service.ensure_candidate(workspace_id, conversation.id, actor_user_id=uuid4())
    conversation.linked_order_id = uuid4()

    state = service.complete_after_order(
        workspace_id,
        conversation.id,
        DirectCustomerCompleteRequest(
            name="Марія Коваль",
            phone="0671234567",
            city="Луцьк",
            region="Волинська",
            recipient_name="Марія Коваль",
            recipient_phone="0671234567",
            warehouse="Відділення №1",
            warehouse_number="1",
            nova_poshta_city_ref="city-ref",
            nova_poshta_warehouse_ref="warehouse-ref",
        ),
        actor_user_id=uuid4(),
    )

    assert prospect.customer.id == state.customer.id
    assert state.linked_order_id == conversation.linked_order_id
    assert state.stage == "CUSTOMER_READY"
    assert state.profile_complete is True
    assert state.missing_fields == []
    customer = service.customers.customers[0]
    assert customer.lifecycle_status == CustomerLifecycleStatus.CUSTOMER.value
    assert customer.profile_status == CustomerProfileStatus.COMPLETE.value
    assert customer.phone == "+380671234567"
    assert customer.city == "Луцьк"
    assert len(service.customer_crm.addresses) == 1
    address = service.customer_crm.addresses[0]
    assert address.nova_poshta_city_ref == "city-ref"
    assert address.nova_poshta_warehouse_ref == "warehouse-ref"
    assert address.is_default is True
