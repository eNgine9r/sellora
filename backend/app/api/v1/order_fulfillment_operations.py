from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.order_fulfillment_operation import FulfillmentExecuteRequest, FulfillmentExecuteResponse, FulfillmentPrepareResponse, FulfillmentRequest, FulfillmentStatusResponse
from app.services.order_fulfillment_service import OrderFulfillmentConflictError, OrderFulfillmentService, OrderFulfillmentServiceError, OrderFulfillmentValidationError

router = APIRouter(prefix="/orders/{order_id}/fulfillment", tags=["Order Fulfillment"])


class FulfillmentCancelRequest(BaseModel):
    cancel_local_operation: bool = True
    cancel_provider_document: bool = False
    release_inventory: bool = False
    reason: str | None = None


@router.post("/prepare", response_model=FulfillmentPrepareResponse)
def prepare_order_fulfillment(order_id: UUID, payload: FulfillmentRequest, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> FulfillmentPrepareResponse:
    return OrderFulfillmentService(db).prepare_fulfillment(workspace_id, order_id, payload)


@router.post("/execute", response_model=FulfillmentExecuteResponse)
def execute_order_fulfillment(order_id: UUID, payload: FulfillmentExecuteRequest, idempotency_key: str = Header(alias="Idempotency-Key"), workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> FulfillmentExecuteResponse:
    try:
        return OrderFulfillmentService(db).execute_fulfillment(workspace_id, order_id, payload, idempotency_key, current_user.id)
    except OrderFulfillmentConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OrderFulfillmentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except OrderFulfillmentServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=FulfillmentStatusResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def get_order_fulfillment(order_id: UUID, workspace_id: UUID = Depends(get_workspace_id), db: Session = Depends(get_db)) -> FulfillmentStatusResponse:
    return OrderFulfillmentService(db).get_fulfillment_status(workspace_id, order_id)


@router.post("/reconcile", response_model=FulfillmentExecuteResponse)
def reconcile_order_fulfillment(order_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> FulfillmentExecuteResponse:
    try:
        return OrderFulfillmentService(db).reconcile_fulfillment(workspace_id, order_id, current_user.id)
    except OrderFulfillmentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/cancel", response_model=FulfillmentStatusResponse)
def cancel_order_fulfillment(order_id: UUID, payload: FulfillmentCancelRequest, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> FulfillmentStatusResponse:
    if payload.cancel_provider_document or payload.release_inventory:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="UNSAFE_CANCEL_COMBINATION_REQUIRES_EXPLICIT_PROVIDER_WORKFLOW")
    try:
        return OrderFulfillmentService(db).cancel_fulfillment(workspace_id, order_id, payload.reason, current_user.id)
    except OrderFulfillmentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
