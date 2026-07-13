from __future__ import annotations

from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.inventory_transaction import InventoryTransaction
from app.models.lead import Lead
from app.models.order import Order
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.workspace import Workspace
from app.models.workspace_user import WorkspaceUser


class OnboardingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def has_configured_workspace(self, workspace: Workspace) -> bool:
        return bool(workspace.name.strip() and workspace.currency_code and workspace.timezone)

    def has_active_product_and_variant(self, workspace_id: UUID) -> bool:
        stmt = select(
            exists().where(
                Product.workspace_id == workspace_id,
                Product.deleted_at.is_(None),
                Product.is_active.is_(True),
                ProductVariant.workspace_id == workspace_id,
                ProductVariant.product_id == Product.id,
                ProductVariant.deleted_at.is_(None),
                ProductVariant.is_active.is_(True),
            )
        )
        return bool(self.db.execute(stmt).scalar())

    def has_positive_stock_transaction(self, workspace_id: UUID) -> bool:
        stmt = select(exists().where(InventoryTransaction.workspace_id == workspace_id, InventoryTransaction.deleted_at.is_(None), InventoryTransaction.quantity > 0))
        return bool(self.db.execute(stmt).scalar())

    def has_lead_or_customer(self, workspace_id: UUID) -> bool:
        lead_stmt = select(exists().where(Lead.workspace_id == workspace_id, Lead.deleted_at.is_(None)))
        customer_stmt = select(exists().where(Customer.workspace_id == workspace_id, Customer.deleted_at.is_(None)))
        return bool(self.db.execute(lead_stmt).scalar()) or bool(self.db.execute(customer_stmt).scalar())

    def has_order(self, workspace_id: UUID) -> bool:
        stmt = select(exists().where(Order.workspace_id == workspace_id, Order.deleted_at.is_(None)))
        return bool(self.db.execute(stmt).scalar())

    def active_membership(self, workspace_id: UUID, user_id: UUID) -> WorkspaceUser | None:
        stmt = select(WorkspaceUser).where(WorkspaceUser.workspace_id == workspace_id, WorkspaceUser.user_id == user_id, WorkspaceUser.is_active.is_(True))
        membership = self.db.execute(stmt).scalar_one_or_none()
        if membership and membership.workspace.is_active:
            return membership
        return None
