from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransaction, InventoryTransactionType
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.inventory_repository import InventoryRepository, InventoryTransactionRepository
from app.schemas.inventory import InventoryTransactionCreate, InventoryUpdate
from app.services.business_utils import snapshot


class InventoryServiceError(ValueError):
    pass


class InventoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.inventory = InventoryRepository(db)
        self.transactions = InventoryTransactionRepository(db)
        self.audit_logs = AuditLogRepository(db)

    def list_inventory(self, workspace_id: UUID, low_stock_only: bool = False) -> list[Inventory]:
        return self.inventory.list_for_workspace(workspace_id, low_stock_only)

    def get_inventory(self, workspace_id: UUID, inventory_id: UUID) -> Inventory | None:
        return self.inventory.get(workspace_id, inventory_id)

    def get_inventory_by_variant(self, workspace_id: UUID, product_variant_id: UUID) -> Inventory | None:
        return self.inventory.get_by_variant(workspace_id, product_variant_id)

    def update_inventory(self, workspace_id: UUID, inventory_id: UUID, payload: InventoryUpdate, actor_user_id: UUID | None) -> Inventory | None:
        inventory = self.inventory.get_for_update(workspace_id, inventory_id)
        if inventory is None:
            return None
        old_value = snapshot(inventory)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(inventory, field, value)
        if inventory.stock_quantity < inventory.reserved_quantity:
            raise InventoryServiceError("Stock quantity cannot be lower than reserved quantity")
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Inventory",
            entity_id=inventory.id,
            action="INVENTORY_ADJUSTMENT",
            old_value=old_value,
            new_value=snapshot(inventory),
        )
        self.db.commit()
        self.db.refresh(inventory)
        return inventory

    def list_transactions(self, workspace_id: UUID, inventory_id: UUID | None = None, product_variant_id: UUID | None = None) -> list[InventoryTransaction]:
        return self.transactions.list_for_workspace(workspace_id, inventory_id, product_variant_id)

    def record_transaction(self, workspace_id: UUID, inventory_id: UUID, payload: InventoryTransactionCreate, actor_user_id: UUID | None, commit: bool = True) -> InventoryTransaction | None:
        inventory = self.inventory.get_for_update(workspace_id, inventory_id)
        if inventory is None:
            return None

        previous_stock = inventory.stock_quantity
        previous_reserved = inventory.reserved_quantity
        new_stock, new_reserved = self._calculate_quantities(inventory, payload.transaction_type, payload.quantity)
        inventory.stock_quantity = new_stock
        inventory.reserved_quantity = new_reserved

        transaction = self.transactions.create(
            InventoryTransaction(
                workspace_id=workspace_id,
                inventory_id=inventory.id,
                product_variant_id=inventory.product_variant_id,
                transaction_type=payload.transaction_type.value,
                quantity=payload.quantity,
                previous_stock_quantity=previous_stock,
                new_stock_quantity=new_stock,
                previous_reserved_quantity=previous_reserved,
                new_reserved_quantity=new_reserved,
                reason=payload.reason,
                created_by=actor_user_id,
            )
        )
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="InventoryTransaction",
            entity_id=transaction.id,
            action=payload.transaction_type.value,
            old_value={"stock_quantity": previous_stock, "reserved_quantity": previous_reserved},
            new_value=snapshot(transaction),
        )
        if commit:
            self.db.commit()
            self.db.refresh(transaction)
        else:
            self.db.flush()
        return transaction

    def _calculate_quantities(self, inventory: Inventory, transaction_type: InventoryTransactionType, quantity: int) -> tuple[int, int]:
        stock = inventory.stock_quantity
        reserved = inventory.reserved_quantity
        available = stock - reserved

        match transaction_type:
            case InventoryTransactionType.STOCK_IN | InventoryTransactionType.RETURN:
                return stock + quantity, reserved
            case InventoryTransactionType.STOCK_OUT:
                if quantity > available:
                    raise InventoryServiceError("Cannot remove more than available stock")
                return stock - quantity, reserved
            case InventoryTransactionType.RESERVE:
                if quantity > available:
                    raise InventoryServiceError("Cannot reserve more than available stock")
                return stock, reserved + quantity
            case InventoryTransactionType.UNRESERVE:
                if quantity > reserved:
                    raise InventoryServiceError("Cannot unreserve more than reserved stock")
                return stock, reserved - quantity
            case InventoryTransactionType.ADJUSTMENT:
                if quantity < reserved:
                    raise InventoryServiceError("Adjusted stock cannot be lower than reserved stock")
                return quantity, reserved
        raise InventoryServiceError("Unsupported inventory transaction type")
