from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransaction


class InventoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, workspace_id: UUID, low_stock_only: bool = False) -> list[Inventory]:
        stmt: Select[tuple[Inventory]] = select(Inventory).where(Inventory.workspace_id == workspace_id, Inventory.deleted_at.is_(None)).options(selectinload(Inventory.variant))
        if low_stock_only:
            stmt = stmt.where(Inventory.stock_quantity <= Inventory.minimum_quantity)
        return list(self.db.execute(stmt.order_by(Inventory.updated_at.desc())).scalars())

    def get(self, workspace_id: UUID, inventory_id: UUID) -> Inventory | None:
        stmt = select(Inventory).where(Inventory.workspace_id == workspace_id, Inventory.id == inventory_id, Inventory.deleted_at.is_(None)).options(selectinload(Inventory.variant))
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_variant(self, workspace_id: UUID, product_variant_id: UUID) -> Inventory | None:
        stmt = select(Inventory).where(Inventory.workspace_id == workspace_id, Inventory.product_variant_id == product_variant_id, Inventory.deleted_at.is_(None)).options(selectinload(Inventory.variant))
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, inventory: Inventory) -> Inventory:
        self.db.add(inventory)
        self.db.flush()
        return inventory


class InventoryTransactionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, workspace_id: UUID, inventory_id: UUID | None = None, product_variant_id: UUID | None = None) -> list[InventoryTransaction]:
        stmt: Select[tuple[InventoryTransaction]] = select(InventoryTransaction).where(InventoryTransaction.workspace_id == workspace_id, InventoryTransaction.deleted_at.is_(None))
        if inventory_id:
            stmt = stmt.where(InventoryTransaction.inventory_id == inventory_id)
        if product_variant_id:
            stmt = stmt.where(InventoryTransaction.product_variant_id == product_variant_id)
        return list(self.db.execute(stmt.order_by(InventoryTransaction.created_at.desc())).scalars())

    def create(self, transaction: InventoryTransaction) -> InventoryTransaction:
        self.db.add(transaction)
        self.db.flush()
        return transaction
