from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.services.business_utils import snapshot


class CustomerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.customers = CustomerRepository(db)
        self.audit_logs = AuditLogRepository(db)

    def list(self, workspace_id: UUID, search: str | None = None) -> list[Customer]:
        return self.customers.list_for_workspace(workspace_id, search)

    def get(self, workspace_id: UUID, customer_id: UUID) -> Customer | None:
        return self.customers.get(workspace_id, customer_id)

    def create(self, workspace_id: UUID, payload: CustomerCreate, actor_user_id: UUID | None) -> Customer:
        customer = self.customers.create(Customer(workspace_id=workspace_id, **payload.model_dump()))
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Customer",
            entity_id=customer.id,
            action="CREATE",
            new_value=snapshot(customer),
        )
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def update(self, workspace_id: UUID, customer_id: UUID, payload: CustomerUpdate, actor_user_id: UUID | None) -> Customer | None:
        customer = self.get(workspace_id, customer_id)
        if customer is None:
            return None
        old_value = snapshot(customer)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(customer, field, value)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Customer",
            entity_id=customer.id,
            action="CUSTOMER_UPDATE",
            old_value=old_value,
            new_value=snapshot(customer),
        )
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def delete(self, workspace_id: UUID, customer_id: UUID, actor_user_id: UUID | None) -> bool:
        customer = self.get(workspace_id, customer_id)
        if customer is None:
            return False
        old_value = snapshot(customer)
        self.customers.soft_delete(customer, actor_user_id)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Customer",
            entity_id=customer.id,
            action="CUSTOMER_ARCHIVE",
            old_value=old_value,
            new_value=snapshot(customer),
        )
        self.db.commit()
        return True
