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

    def refresh(self, _model, attribute_names=None):
        pass


class FakeConversationRepository:
    def __init__(self, conversation):
        self.conversation = conversation

    def get_for_update_nowait(self, workspace_id, conversation_id):
        return self.get(workspace_id, conversation_id)

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

    def try_lock_direct_matching(self, workspace_id):
        return True

    def get(self, workspace_id, customer_id):
        return next((item for item in self.customers if item.workspace_id == workspace_id and item.id == customer_id), None)

    def get_for_update(self, workspace_id, customer_id):
        return self.get(workspace_id, customer_id)

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

    def list_instagram_identity_candidates(self, workspace_id, instagram_scoped_id, instagram_username, limit=20):
        normalized = (instagram_username or "").strip().lstrip("@").lower()
        return [item for item in self.customers if item.workspace_id == workspace_id and (
            (instagram_scoped_id and item.instagram_scoped_id == instagram_scoped_id)
            or (normalized and (item.instagram_username or "").strip().lstrip("@").lower() == normalized)
        )][:limit]

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
    service.ad_attribution = SimpleNamespace(inherit_verified_direct_lead=lambda *args, **kwargs: False)
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


def test_busy_matching_never_creates_or_links_a_customer():
    import pytest
    from app.services.direct_customer_automation_service import DirectCustomerAutomationError

    service, conversation, workspace_id = make_service()
    service.customers.try_lock_direct_matching = lambda _workspace_id: False
    with pytest.raises(DirectCustomerAutomationError, match="DIRECT_CUSTOMER_IDENTITY_BUSY"):
        service.ensure_candidate(workspace_id, conversation.id, actor_user_id=uuid4())
    assert not service.customers.customers
    assert conversation.linked_customer_id is None


def test_manager_links_reviewed_candidate_without_overwriting_identifiers():
    from app.models.customer import Customer

    service, conversation, workspace_id = make_service()
    customer = service.customers.create(Customer(
        workspace_id=workspace_id, name="Existing", instagram_username="buyer_one",
        instagram_scoped_id="different-connection-id", phone=None,
        source=CustomerSource.MANUAL.value, lifecycle_status=CustomerLifecycleStatus.CUSTOMER.value,
        profile_status=CustomerProfileStatus.INCOMPLETE.value,
    ))
    actor = uuid4()
    candidates = service.identity_candidates(workspace_id, conversation.id)
    assert [item.id for item in candidates] == [customer.id]
    state = service.link_identity_candidate(workspace_id, conversation.id, customer.id, actor)
    assert state.customer.id == customer.id
    assert conversation.linked_customer_id == customer.id
    assert customer.instagram_scoped_id == "different-connection-id"
    assert service.audit_logs.records[-1]["user_id"] == actor
    assert service.audit_logs.records[-1]["new_value"]["identity_reviewed"] is True


def test_review_never_links_non_matching_or_other_workspace_customer():
    import pytest
    from app.models.customer import Customer
    from app.services.direct_customer_automation_service import DirectCustomerAutomationError

    service, conversation, workspace_id = make_service()
    foreign = service.customers.create(Customer(workspace_id=uuid4(), name="Foreign", instagram_username="buyer_one"))
    nonmatching = service.customers.create(Customer(workspace_id=workspace_id, name="Other", instagram_username="other"))
    for customer in (foreign, nonmatching):
        with pytest.raises(DirectCustomerAutomationError, match="DIRECT_CUSTOMER_CANDIDATE_CHANGED"):
            service.link_identity_candidate(workspace_id, conversation.id, customer.id, uuid4())
    assert conversation.linked_customer_id is None


def test_review_never_replaces_existing_link_or_linked_order():
    import pytest
    from app.models.customer import Customer
    from app.services.direct_customer_automation_service import DirectCustomerAutomationError

    service, conversation, workspace_id = make_service()
    customer = service.customers.create(Customer(workspace_id=workspace_id, name="Existing", instagram_username="buyer_one"))
    for field in ("linked_customer_id", "linked_order_id"):
        setattr(conversation, field, uuid4())
        with pytest.raises(DirectCustomerAutomationError, match="DIRECT_CUSTOMER_ALREADY_LINKED"):
            service.link_identity_candidate(workspace_id, conversation.id, customer.id, uuid4())
        setattr(conversation, field, None)


def test_cross_connection_scoped_identity_requires_review():
    import pytest
    from app.models.customer import Customer
    from app.services.direct_customer_automation_service import DirectCustomerAutomationError

    service, conversation, workspace_id = make_service()
    conversation.instagram_connection_id = uuid4()
    customer = service.customers.create(Customer(workspace_id=workspace_id, name="Existing", instagram_username="buyer_one", instagram_scoped_id="igs-user-1", source_direct_conversation_id=uuid4()))
    with pytest.raises(DirectCustomerAutomationError, match="DIRECT_CUSTOMER_IDENTITY_CONFLICT"):
        service.ensure_candidate(workspace_id, conversation.id, uuid4())
    assert conversation.linked_customer_id is None
    assert len(service.customers.customers) == 1
    assert service.customers.customers[0] is customer


def test_same_connection_scoped_identity_with_matching_source_can_link():
    from app.models.customer import Customer

    service, conversation, workspace_id = make_service()
    conversation.instagram_connection_id = uuid4()
    customer = service.customers.create(Customer(
        workspace_id=workspace_id, name="Existing", instagram_username="buyer_one",
        instagram_scoped_id="igs-user-1", source_direct_conversation_id=conversation.id,
        source=CustomerSource.MANUAL.value, lifecycle_status=CustomerLifecycleStatus.CUSTOMER.value,
        profile_status=CustomerProfileStatus.INCOMPLETE.value,
    ))
    state = service.ensure_candidate(workspace_id, conversation.id, uuid4())
    assert state.customer.id == customer.id
    assert conversation.linked_customer_id == customer.id


def test_same_connection_with_wrong_source_scoped_id_requires_review():
    import pytest
    from app.models.customer import Customer
    from app.services.direct_customer_automation_service import DirectCustomerAutomationError

    service, conversation, workspace_id = make_service()
    conversation.instagram_connection_id = uuid4()
    customer = service.customers.create(Customer(
        workspace_id=workspace_id, name="Existing", instagram_username="buyer_one",
        instagram_scoped_id="igs-user-1", source_direct_conversation_id=uuid4(),
    ))
    original_get = service.conversations.get
    def get_source(workspace, conversation_id):
        if conversation_id == customer.source_direct_conversation_id:
            return SimpleNamespace(instagram_connection_id=conversation.instagram_connection_id, participant_scoped_id="different")
        return original_get(workspace, conversation_id)
    service.conversations.get = get_source
    with pytest.raises(DirectCustomerAutomationError, match="DIRECT_CUSTOMER_IDENTITY_CONFLICT"):
        service.ensure_candidate(workspace_id, conversation.id, uuid4())
    assert conversation.linked_customer_id is None


def test_review_rechecks_identity_after_locking_customer():
    import pytest
    from app.models.customer import Customer
    from app.services.direct_customer_automation_service import DirectCustomerAutomationError

    service, conversation, workspace_id = make_service()
    customer = service.customers.create(Customer(workspace_id=workspace_id, name="Existing", instagram_username="buyer_one"))
    def changed_after_listing(_workspace_id, _customer_id):
        customer.instagram_username = "different_username"
        return customer
    service.customers.get_for_update = changed_after_listing
    with pytest.raises(DirectCustomerAutomationError, match="DIRECT_CUSTOMER_CANDIDATE_CHANGED"):
        service.link_identity_candidate(workspace_id, conversation.id, customer.id, uuid4())
    assert conversation.linked_customer_id is None


def test_busy_conversation_never_creates_or_links_a_customer():
    import pytest
    from app.repositories.ai_direct_repository import DirectConversationBusy
    from app.services.direct_customer_automation_service import DirectCustomerAutomationError

    service, conversation, workspace_id = make_service()
    def busy(_workspace_id, _conversation_id):
        raise DirectConversationBusy()
    service.conversations.get_for_update_nowait = busy
    with pytest.raises(DirectCustomerAutomationError, match="DIRECT_CUSTOMER_IDENTITY_BUSY"):
        service.ensure_candidate(workspace_id, conversation.id, uuid4())
    assert not service.customers.customers
    assert conversation.linked_customer_id is None


def test_automatic_match_rechecks_customer_after_locking():
    import pytest
    from app.models.customer import Customer
    from app.services.direct_customer_automation_service import DirectCustomerAutomationError

    service, conversation, workspace_id = make_service()
    customer = service.customers.create(Customer(workspace_id=workspace_id, name="Existing", instagram_username="buyer_one"))
    def changed_after_lookup(_workspace_id, _customer_id):
        customer.instagram_username = "different_username"
        return customer
    service.customers.get_for_update = changed_after_lookup
    with pytest.raises(DirectCustomerAutomationError, match="DIRECT_CUSTOMER_IDENTITY_CONFLICT"):
        service.ensure_candidate(workspace_id, conversation.id, uuid4())
    assert conversation.linked_customer_id is None
