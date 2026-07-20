from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.order_repository import OrderRepository
from app.schemas.direct_customer_automation import (
    DirectCustomerAutomationState,
    DirectCustomerCompleteRequest,
    DirectCustomerFinalizeOrderRequest,
)
from app.services.direct_customer_automation_service import (
    DirectCustomerAutomationError,
    DirectCustomerAutomationService,
)


class DirectCustomerOrderFinalizationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.automation = DirectCustomerAutomationService(db)

    def finalize(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        payload: DirectCustomerFinalizeOrderRequest,
        actor_user_id: UUID | None,
    ) -> DirectCustomerAutomationState:
        order = self.orders.get(workspace_id, payload.order_id)
        if order is None:
            raise DirectCustomerAutomationError("DIRECT_ORDER_NOT_FOUND")
        state = self.automation.ensure_candidate(
            workspace_id,
            conversation_id,
            actor_user_id,
            commit=False,
        )
        if state.customer is None:
            raise DirectCustomerAutomationError("DIRECT_CUSTOMER_NOT_FOUND")
        if order.customer_id != state.customer.id:
            raise DirectCustomerAutomationError("DIRECT_ORDER_CUSTOMER_MISMATCH")
        customer = self.automation.customers.get(workspace_id, state.customer.id)
        if customer is None:
            raise DirectCustomerAutomationError("DIRECT_CUSTOMER_NOT_FOUND")
        self.automation.link_fulfillment_result(
            workspace_id,
            conversation_id,
            customer,
            order.id,
            recipient_name=(payload.recipient_name or payload.name),
            recipient_phone=payload.recipient_phone or payload.phone,
            city=payload.city,
            actor_user_id=actor_user_id,
        )
        return self.automation.complete_after_order(
            workspace_id,
            conversation_id,
            DirectCustomerCompleteRequest(**payload.model_dump(exclude={"order_id"})),
            actor_user_id,
        )
