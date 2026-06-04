from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.order import OrderStatus
from app.models.role import RoleName
from app.models.user import User
from app.schemas.order import OrderCreate, OrderDashboardResponse, OrderResponse, OrderStatusUpdate, OrderUpdate
from app.schemas.shipment import ShipmentCreate, ShipmentResponse
from app.services.order_service import OrderService, OrderServiceError
from app.services.shipment_service import ShipmentService, ShipmentServiceError

router = APIRouter(prefix="/orders", tags=["Orders"])


def _bad_request(exc: OrderServiceError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/dashboard", response_model=OrderDashboardResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def dashboard(workspace_id: UUID = Depends(get_workspace_id), db: Session = Depends(get_db)) -> OrderDashboardResponse:
    return OrderService(db).dashboard_today(workspace_id)


@router.get("", response_model=list[OrderResponse], dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def list_orders(workspace_id: UUID = Depends(get_workspace_id), order_status: OrderStatus | None = Query(default=None, alias="status"), db: Session = Depends(get_db)) -> list[OrderResponse]:
    return OrderService(db).list(workspace_id, order_status)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> OrderResponse:
    try:
        return OrderService(db).create(workspace_id, payload, current_user.id)
    except OrderServiceError as exc:
        raise _bad_request(exc)


@router.get("/{order_id}", response_model=OrderResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def get_order(order_id: UUID, workspace_id: UUID = Depends(get_workspace_id), db: Session = Depends(get_db)) -> OrderResponse:
    order = OrderService(db).get(workspace_id, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(order_id: UUID, payload: OrderUpdate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> OrderResponse:
    order = OrderService(db).update(workspace_id, order_id, payload, current_user.id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> Response:
    try:
        deleted = OrderService(db).delete(workspace_id, order_id, current_user.id)
    except OrderServiceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{order_id}/status", response_model=OrderResponse)
def change_order_status(order_id: UUID, payload: OrderStatusUpdate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> OrderResponse:
    try:
        order = OrderService(db).change_status(workspace_id, order_id, payload, current_user.id)
    except OrderServiceError as exc:
        raise _bad_request(exc)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.get("/{order_id}/shipment", response_model=ShipmentResponse | None, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def get_order_shipment(order_id: UUID, workspace_id: UUID = Depends(get_workspace_id), db: Session = Depends(get_db)) -> ShipmentResponse | None:
    try:
        return ShipmentService(db).get_for_order(workspace_id, order_id)
    except ShipmentServiceError as exc:
        raise _bad_request(OrderServiceError(str(exc)))


@router.post("/{order_id}/shipment", response_model=ShipmentResponse, status_code=status.HTTP_201_CREATED)
def create_order_shipment(order_id: UUID, payload: ShipmentCreate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> ShipmentResponse:
    try:
        return ShipmentService(db).create(workspace_id, payload.model_copy(update={"order_id": order_id}), current_user.id)
    except ShipmentServiceError as exc:
        raise _bad_request(OrderServiceError(str(exc)))
