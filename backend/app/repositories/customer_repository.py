from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer


class CustomerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_workspace(self, workspace_id: UUID, search: str | None = None) -> list[Customer]:
        stmt: Select[tuple[Customer]] = select(Customer).where(Customer.workspace_id == workspace_id, Customer.deleted_at.is_(None))
        if search:
            query = f"%{search}%"
            stmt = stmt.where(or_(Customer.name.ilike(query), Customer.phone.ilike(query), Customer.instagram_username.ilike(query)))
        return list(self.db.execute(stmt.order_by(Customer.created_at.desc())).scalars())

    def get(self, workspace_id: UUID, customer_id: UUID) -> Customer | None:
        stmt = select(Customer).where(Customer.workspace_id == workspace_id, Customer.id == customer_id, Customer.deleted_at.is_(None))
        return self.db.execute(stmt).scalar_one_or_none()

    def find_by_instagram_identity(self, workspace_id: UUID, instagram_scoped_id: str | None = None, instagram_username: str | None = None) -> Customer | None:
        identity_filters = []
        if instagram_scoped_id:
            identity_filters.append(Customer.instagram_scoped_id == instagram_scoped_id)
        normalized_username = (instagram_username or "").strip().lstrip("@").lower()
        if normalized_username:
            identity_filters.append(func.lower(Customer.instagram_username) == normalized_username)
        if not identity_filters:
            return None
        statement = select(Customer).where(
            Customer.workspace_id == workspace_id,
            Customer.deleted_at.is_(None),
            or_(*identity_filters),
        ).order_by(Customer.created_at.asc()).limit(1)
        return self.db.execute(statement).scalar_one_or_none()

    def create(self, customer: Customer) -> Customer:
        self.db.add(customer)
        self.db.flush()
        return customer

    def soft_delete(self, customer: Customer, deleted_by: UUID | None) -> Customer:
        customer.deleted_at = datetime.now(UTC)
        customer.deleted_by = deleted_by
        self.db.flush()
        return customer
