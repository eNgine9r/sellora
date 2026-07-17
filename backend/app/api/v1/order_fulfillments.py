from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.order_fulfillment import OrderFulfillmentCreate, OrderFulfillmentResponse
from app.services.order_fulfillment_service import (
    OrderFulfillmentConflictError,
    OrderFulfillmentService,
    OrderFulfillmentServiceError,
    OrderFulfillmentValidationError,
)

router = APIRouter(prefix="/order-fulfillments", tags=["Order Fulfillments"])


@router.post("", response_model=OrderFulfillmentResponse, status_code=status.HTTP_201_CREATED)
def create_order_fulfillment(
    payload: OrderFulfillmentCreate,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> OrderFulfillmentResponse:
    try:
        return OrderFulfillmentService(db).create(workspace_id, payload, current_user.id)
    except OrderFulfillmentConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OrderFulfillmentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except OrderFulfillmentServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
