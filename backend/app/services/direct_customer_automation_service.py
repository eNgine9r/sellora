from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.services.direct_order_intent_service import detect_direct_order_intent
from app.models.customer import (
    Customer,
    CustomerLifecycleStatus,
    CustomerProfileStatus,
    CustomerSource,
)
from app.models.customer_address import DeliveryProvider
from app.repositories.ai_direct_repository import DirectConversationRepository, DirectMessageRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.customer_repository import CustomerRepository
from app.schemas.crm_completion import CustomerAddressCreate, CustomerAddressUpdate
from app.schemas.customer import CustomerResponse
from app.schemas.direct_customer_automation import (
    DirectCustomerAutomationState,
    DirectCustomerCompleteRequest,
)
from app.services.business_utils import snapshot
from app.services.crm_completion_service import CustomerCrmService


class DirectCustomerAutomationError(ValueError):
    pass


class DirectCustomerAutomationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.conversations = DirectConversationRepository(db)
        self.messages = DirectMessageRepository(db)
        self.customers = CustomerRepository(db)
        self.customer_crm = CustomerCrmService(db)
        self.audit_logs = AuditLogRepository(db)

    def state(self, workspace_id: UUID, conversation_id: UUID) -> DirectCustomerAutomationState:
        conversation = self._conversation(workspace_id, conversation_id)
        customer = self.customers.get(workspace_id, conversation.linked_customer_id) if conversation.linked_customer_id else None
        return self._state(workspace_id, conversation, customer)

    def ensure_candidate(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        actor_user_id: UUID | None,
        *,
        require_order_intent: bool = False,
        commit: bool = True,
    ) -> DirectCustomerAutomationState:
        conversation = self._conversation(workspace_id, conversation_id)
        latest = self.messages.latest_analyzable(workspace_id, conversation_id)
        if require_order_intent and not detect_direct_order_intent(latest.text if latest else None).detected:
            return self._state(workspace_id, conversation, None)

        existing = self.customers.get(workspace_id, conversation.linked_customer_id) if conversation.linked_customer_id else None
        created = False
        customer = existing or self.customers.find_by_instagram_identity(
            workspace_id,
            instagram_scoped_id=conversation.participant_scoped_id,
            instagram_username=conversation.participant_username,
        )
        if customer is None:
            display_name = self._display_name(conversation)
            customer = self.customers.create(
                Customer(
                    workspace_id=workspace_id,
                    name=display_name,
                    phone=None,
                    instagram_username=self._username(conversation.participant_username),
                    instagram_scoped_id=conversation.participant_scoped_id,
                    source=CustomerSource.INSTAGRAM_DIRECT.value,
                    lifecycle_status=CustomerLifecycleStatus.PROSPECT.value,
                    profile_status=CustomerProfileStatus.INCOMPLETE.value,
                    source_direct_conversation_id=conversation.id,
                )
            )
            created = True
            self.audit_logs.create(
                workspace_id=workspace_id,
                user_id=actor_user_id,
                entity_type="Customer",
                entity_id=customer.id,
                action="DIRECT_PROSPECT_CREATE",
                new_value=snapshot(customer),
            )
        else:
            self._sync_identity(customer, conversation)

        conversation.linked_customer_id = customer.id
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="DirectConversation",
            entity_id=conversation.id,
            action="DIRECT_CUSTOMER_LINK",
            new_value={"customer_id": str(customer.id), "automatic": actor_user_id is None},
        )
        if commit:
            self.db.commit()
            self.db.refresh(customer)
        else:
            self.db.flush()
        state = self._state(workspace_id, conversation, customer)
        state.created_automatically = created and actor_user_id is None
        return state

    def ensure_from_inbound_order_intent(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        message_text: str | None,
    ) -> DirectCustomerAutomationState | None:
        if not detect_direct_order_intent(message_text).detected:
            return None
        return self.ensure_candidate(
            workspace_id,
            conversation_id,
            actor_user_id=None,
            require_order_intent=False,
            commit=False,
        )

    def complete_after_order(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        payload: DirectCustomerCompleteRequest,
        actor_user_id: UUID | None,
    ) -> DirectCustomerAutomationState:
        conversation = self._conversation(workspace_id, conversation_id)
        if conversation.linked_order_id is None:
            raise DirectCustomerAutomationError("DIRECT_ORDER_REQUIRED")
        state = self.ensure_candidate(workspace_id, conversation_id, actor_user_id, commit=False)
        customer = self.customers.get(workspace_id, state.customer.id) if state.customer else None
        if customer is None:
            raise DirectCustomerAutomationError("DIRECT_CUSTOMER_NOT_FOUND")
        old_value = snapshot(customer)
        customer.name = payload.name.strip()
        customer.phone = payload.phone
        customer.city = payload.city.strip()
        customer.region = payload.region.strip() if payload.region else None
        customer.lifecycle_status = CustomerLifecycleStatus.CUSTOMER.value
        customer.profile_status = CustomerProfileStatus.COMPLETE.value
        customer.source_direct_conversation_id = conversation.id
        self._sync_identity(customer, conversation)
        self._upsert_default_address(
            workspace_id,
            customer.id,
            recipient_name=(payload.recipient_name or payload.name).strip(),
            recipient_phone=payload.recipient_phone or payload.phone,
            city=payload.city.strip(),
            warehouse=payload.warehouse.strip(),
            warehouse_number=payload.warehouse_number,
            city_ref=payload.nova_poshta_city_ref,
            warehouse_ref=payload.nova_poshta_warehouse_ref,
            actor_user_id=actor_user_id,
        )
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Customer",
            entity_id=customer.id,
            action="DIRECT_CUSTOMER_PROFILE_COMPLETE",
            old_value=old_value,
            new_value=snapshot(customer),
        )
        self.db.commit()
        self.db.refresh(customer)
        return self._state(workspace_id, conversation, customer)

    def link_fulfillment_result(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        customer: Customer,
        order_id: UUID,
        *,
        recipient_name: str,
        recipient_phone: str,
        city: str,
        actor_user_id: UUID | None,
    ) -> None:
        conversation = self._conversation(workspace_id, conversation_id)
        if customer.workspace_id != workspace_id:
            raise DirectCustomerAutomationError("DIRECT_CUSTOMER_WORKSPACE_MISMATCH")
        old_value = snapshot(customer)
        conversation.linked_customer_id = customer.id
        conversation.linked_order_id = order_id
        customer.name = recipient_name.strip() or customer.name
        customer.phone = recipient_phone or customer.phone
        customer.city = city.strip() or customer.city
        customer.lifecycle_status = CustomerLifecycleStatus.CUSTOMER.value
        customer.profile_status = CustomerProfileStatus.COMPLETE.value
        customer.source_direct_conversation_id = conversation.id
        self._sync_identity(customer, conversation)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="DirectConversation",
            entity_id=conversation.id,
            action="DIRECT_ORDER_LINK",
            new_value={"customer_id": str(customer.id), "order_id": str(order_id)},
        )
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Customer",
            entity_id=customer.id,
            action="DIRECT_CUSTOMER_CONVERT",
            old_value=old_value,
            new_value=snapshot(customer),
        )
        self.db.flush()

    def _conversation(self, workspace_id: UUID, conversation_id: UUID):
        conversation = self.conversations.get(workspace_id, conversation_id)
        if conversation is None:
            raise DirectCustomerAutomationError("DIRECT_CONVERSATION_NOT_FOUND")
        return conversation

    def _state(self, workspace_id: UUID, conversation, customer: Customer | None) -> DirectCustomerAutomationState:
        missing: list[str] = []
        has_address = False
        if customer:
            if not customer.name or customer.name == "Instagram customer":
                missing.append("name")
            if not customer.phone:
                missing.append("phone")
            if not customer.city:
                missing.append("city")
            addresses = self.customer_crm.list_addresses(workspace_id, customer.id)
            has_address = any(
                address.address_line1 and address.city and address.nova_poshta_city_ref and address.nova_poshta_warehouse_ref
                for address in addresses
            )
            if not has_address:
                missing.append("delivery_address")
        profile_complete = bool(customer and not missing)
        if conversation.linked_order_id and profile_complete:
            stage = "CUSTOMER_READY"
        elif conversation.linked_order_id:
            stage = "ORDER_CREATED_PROFILE_INCOMPLETE"
        elif customer:
            stage = "PROSPECT_READY_FOR_ORDER"
        else:
            stage = "NOT_CREATED"
        return DirectCustomerAutomationState(
            conversation_id=conversation.id,
            customer=CustomerResponse.model_validate(customer) if customer else None,
            linked_order_id=conversation.linked_order_id,
            stage=stage,
            missing_fields=missing,
            can_create_order=customer is not None and conversation.linked_order_id is None,
            profile_complete=profile_complete,
        )

    def _sync_identity(self, customer: Customer, conversation) -> None:
        if conversation.participant_scoped_id and not customer.instagram_scoped_id:
            customer.instagram_scoped_id = conversation.participant_scoped_id
        username = self._username(conversation.participant_username)
        if username and not customer.instagram_username:
            customer.instagram_username = username
        if (not customer.name or customer.name == "Instagram customer") and conversation.participant_display_name:
            customer.name = conversation.participant_display_name
        if customer.source == CustomerSource.MANUAL.value and customer.lifecycle_status == CustomerLifecycleStatus.PROSPECT.value:
            customer.source = CustomerSource.INSTAGRAM_DIRECT.value
        if not customer.source_direct_conversation_id:
            customer.source_direct_conversation_id = conversation.id

    def _upsert_default_address(
        self,
        workspace_id: UUID,
        customer_id: UUID,
        *,
        recipient_name: str,
        recipient_phone: str,
        city: str,
        warehouse: str,
        warehouse_number: str | None,
        city_ref: str,
        warehouse_ref: str,
        actor_user_id: UUID | None,
    ) -> None:
        values = dict(
            label="Нова Пошта",
            recipient_name=recipient_name,
            phone=recipient_phone,
            address_line1=warehouse,
            city=city,
            country="Україна",
            is_default=True,
            delivery_provider=DeliveryProvider.NOVA_POSHTA,
            nova_poshta_city_ref=city_ref,
            nova_poshta_warehouse_ref=warehouse_ref,
            warehouse_number=warehouse_number,
        )
        addresses = self.customer_crm.list_addresses(workspace_id, customer_id)
        current = next((address for address in addresses if address.is_default), None)
        if current:
            self.customer_crm.update_address(
                workspace_id,
                customer_id,
                current.id,
                CustomerAddressUpdate(**values),
                actor_user_id,
                commit=False,
            )
        else:
            self.customer_crm.add_address(
                workspace_id,
                customer_id,
                CustomerAddressCreate(**values),
                actor_user_id,
                commit=False,
            )

    @staticmethod
    def _username(value: str | None) -> str | None:
        normalized = (value or "").strip().lstrip("@")
        return normalized or None

    @staticmethod
    def _display_name(conversation) -> str:
        display = (conversation.participant_display_name or "").strip()
        if display and display != "Instagram customer":
            return display
        username = DirectCustomerAutomationService._username(conversation.participant_username)
        return f"@{username}" if username else "Instagram customer"
