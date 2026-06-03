from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.inventory_transaction import InventoryTransactionType


class InventoryResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    product_variant_id: UUID
    stock_quantity: int
    reserved_quantity: int
    minimum_quantity: int
    is_low_stock: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryUpdate(BaseModel):
    minimum_quantity: int | None = Field(default=None, ge=0)


class InventoryTransactionCreate(BaseModel):
    transaction_type: InventoryTransactionType
    quantity: int = Field(gt=0)
    reason: str | None = None


class InventoryTransactionResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    inventory_id: UUID
    product_variant_id: UUID
    transaction_type: InventoryTransactionType
    quantity: int
    previous_stock_quantity: int
    new_stock_quantity: int
    previous_reserved_quantity: int
    new_reserved_quantity: int
    reason: str | None
    created_by: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
