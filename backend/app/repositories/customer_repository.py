from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer


class InstagramIdentityConflict(ValueError):
    """Matching customer identities require manual verification."""


def select_instagram_identity(candidates, instagram_scoped_id: str | None):
    # A username can change or be reused; multiple matching records or a
    # conflicting scoped ID cannot safely be resolved automatically.
    if len(candidates) > 1:
        raise InstagramIdentityConflict("DIRECT_CUSTOMER_IDENTITY_CONFLICT")
    if not candidates:
        return None
    candidate = candidates[0]
    if instagram_scoped_id and candidate.instagram_scoped_id and candidate.instagram_scoped_id != instagram_scoped_id:
        raise InstagramIdentityConflict("DIRECT_CUSTOMER_IDENTITY_CONFLICT")
    return candidate


class CustomerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def try_lock_direct_matching(self, workspace_id: UUID) -> bool:
        # Never wait while a webhook batch may hold other transaction locks.
        # Direct matching and manager review use the same transaction lock.
        if self.db.get_bind().dialect.name != "postgresql":
            return True
        key = int.from_bytes(hashlib.sha256(f"sellora:direct-customer:{workspace_id}".encode()).digest()[:8], "big", signed=True)
        return bool(self.db.scalar(select(func.pg_try_advisory_xact_lock(key))))

    def list_for_workspace(self, workspace_id: UUID, search: str | None = None) -> list[Customer]:
        stmt: Select[tuple[Customer]] = select(Customer).where(Customer.workspace_id == workspace_id, Customer.deleted_at.is_(None))
        if search:
            query = f"%{search}%"
            stmt = stmt.where(or_(Customer.name.ilike(query), Customer.phone.ilike(query), Customer.instagram_username.ilike(query)))
        return list(self.db.execute(stmt.order_by(Customer.created_at.desc())).scalars())

    def get(self, workspace_id: UUID, customer_id: UUID) -> Customer | None:
        stmt = select(Customer).where(Customer.workspace_id == workspace_id, Customer.id == customer_id, Customer.deleted_at.is_(None))
        return self.db.execute(stmt).scalar_one_or_none()

    def get_for_update(self, workspace_id: UUID, customer_id: UUID) -> Customer | None:
        statement = select(Customer).where(
            Customer.workspace_id == workspace_id, Customer.id == customer_id, Customer.deleted_at.is_(None),
        ).with_for_update().execution_options(populate_existing=True)
        return self.db.execute(statement).scalar_one_or_none()

    def find_by_instagram_identity(self, workspace_id: UUID, instagram_scoped_id: str | None = None, instagram_username: str | None = None) -> Customer | None:
        candidates = self.list_instagram_identity_candidates(workspace_id, instagram_scoped_id, instagram_username, limit=2)
        return select_instagram_identity(candidates, instagram_scoped_id)

    def list_instagram_identity_candidates(self, workspace_id: UUID, instagram_scoped_id: str | None, instagram_username: str | None, limit: int = 20) -> list[Customer]:
        identity_filters = []
        if instagram_scoped_id:
            identity_filters.append(Customer.instagram_scoped_id == instagram_scoped_id)
        normalized_username = (instagram_username or "").strip().lstrip("@").lower()
        if normalized_username:
            identity_filters.append(func.ltrim(func.trim(func.lower(Customer.instagram_username)), "@") == normalized_username)
        if not identity_filters:
            return []
        statement = select(Customer).where(
            Customer.workspace_id == workspace_id,
            Customer.deleted_at.is_(None),
            or_(*identity_filters),
        ).order_by(Customer.created_at.asc(), Customer.id.asc()).limit(limit)
        return list(self.db.execute(statement).scalars())

    def create(self, customer: Customer) -> Customer:
        self.db.add(customer)
        self.db.flush()
        return customer

    def soft_delete(self, customer: Customer, deleted_by: UUID | None) -> Customer:
        customer.deleted_at = datetime.now(UTC)
        customer.deleted_by = deleted_by
        self.db.flush()
        return customer
