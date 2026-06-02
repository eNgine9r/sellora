from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer


class CustomerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, workspace_id: UUID, search: str | None = None) -> list[Customer]:
        stmt: Select[tuple[Customer]] = select(Customer).where(Customer.workspace_id == workspace_id, Customer.deleted_at.is_(None))
        if search:
            query = f"%{search}%"
            stmt = stmt.where(or_(Customer.name.ilike(query), Customer.phone.ilike(query), Customer.instagram_username.ilike(query)))
        return list(self.db.execute(stmt.order_by(Customer.created_at.desc())).scalars())

    def get(self, workspace_id: UUID, customer_id: UUID) -> Customer | None:
        stmt = select(Customer).where(Customer.workspace_id == workspace_id, Customer.id == customer_id, Customer.deleted_at.is_(None))
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, customer: Customer) -> Customer:
        self.db.add(customer)
        self.db.flush()
        return customer

    def soft_delete(self, customer: Customer, deleted_by: UUID | None) -> Customer:
        customer.deleted_at = datetime.now(UTC)
        customer.deleted_by = deleted_by
        self.db.flush()
        return customer
