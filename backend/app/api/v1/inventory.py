from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.inventory import InventoryResponse, InventoryTransactionCreate, InventoryTransactionResponse, InventoryUpdate
from app.services.inventory_service import InventoryService, InventoryServiceError

router = APIRouter(prefix="/inventory", tags=["Inventory"])


def _bad_request(exc: InventoryServiceError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=list[InventoryResponse], dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def list_inventory(workspace_id: UUID = Depends(get_workspace_id), low_stock_only: bool = Query(default=False), db: Session = Depends(get_db)) -> list[InventoryResponse]:
    return InventoryService(db).list_inventory(workspace_id, low_stock_only)


@router.get("/transactions", response_model=list[InventoryTransactionResponse], dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def list_inventory_transactions(
    workspace_id: UUID = Depends(get_workspace_id),
    inventory_id: UUID | None = Query(default=None),
    product_variant_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[InventoryTransactionResponse]:
    return InventoryService(db).list_transactions(workspace_id, inventory_id, product_variant_id)


@router.get("/{inventory_id}", response_model=InventoryResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def get_inventory(inventory_id: UUID, workspace_id: UUID = Depends(get_workspace_id), db: Session = Depends(get_db)) -> InventoryResponse:
    inventory = InventoryService(db).get_inventory(workspace_id, inventory_id)
    if inventory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory record not found")
    return inventory


@router.put("/{inventory_id}", response_model=InventoryResponse)
def update_inventory(inventory_id: UUID, payload: InventoryUpdate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> InventoryResponse:
    inventory = InventoryService(db).update_inventory(workspace_id, inventory_id, payload, current_user.id)
    if inventory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory record not found")
    return inventory


@router.post("/{inventory_id}/transactions", response_model=InventoryTransactionResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_transaction(inventory_id: UUID, payload: InventoryTransactionCreate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> InventoryTransactionResponse:
    try:
        transaction = InventoryService(db).record_transaction(workspace_id, inventory_id, payload, current_user.id)
    except InventoryServiceError as exc:
        raise _bad_request(exc)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory record not found")
    return transaction
