from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.shipment import ShipmentStatus
from app.models.user import User
from app.schemas.integration import NovaPoshtaStatusResponse, NovaPoshtaTtnResponse
from app.schemas.shipment import ShipmentCreate, ShipmentResponse, ShipmentSummaryResponse, ShipmentUpdate
from app.services.nova_poshta_provider_service import NovaPoshtaProviderShipmentService
from app.services.nova_poshta_service import NovaPoshtaServiceError
from app.services.shipment_service import ShipmentService, ShipmentServiceError

router = APIRouter(prefix="/shipments", tags=["Shipments"])


def _bad_request(exc: ShipmentServiceError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/summary", response_model=ShipmentSummaryResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def summary(workspace_id: UUID = Depends(get_workspace_id), db: Session = Depends(get_db)) -> ShipmentSummaryResponse:
    return ShipmentService(db).summary(workspace_id)


@router.get("", response_model=list[ShipmentResponse], dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def list_shipments(workspace_id: UUID = Depends(get_workspace_id), shipment_status: ShipmentStatus | None = Query(default=None, alias="status"), search: str | None = None, db: Session = Depends(get_db)) -> list[ShipmentResponse]:
    return ShipmentService(db).list(workspace_id, shipment_status, search)


@router.post("", response_model=ShipmentResponse, status_code=status.HTTP_201_CREATED)
def create_shipment(payload: ShipmentCreate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> ShipmentResponse:
    try:
        return ShipmentService(db).create(workspace_id, payload, current_user.id)
    except ShipmentServiceError as exc:
        raise _bad_request(exc)


@router.get("/{shipment_id}", response_model=ShipmentResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def get_shipment(shipment_id: UUID, workspace_id: UUID = Depends(get_workspace_id), db: Session = Depends(get_db)) -> ShipmentResponse:
    shipment = ShipmentService(db).get(workspace_id, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    return shipment


@router.put("/{shipment_id}", response_model=ShipmentResponse)
def update_shipment(shipment_id: UUID, payload: ShipmentUpdate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> ShipmentResponse:
    try:
        shipment = ShipmentService(db).update(workspace_id, shipment_id, payload, current_user.id)
    except ShipmentServiceError as exc:
        raise _bad_request(exc)
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    return shipment


@router.delete("/{shipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shipment(shipment_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> None:
    if not ShipmentService(db).delete(workspace_id, shipment_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")


def _mark_status(shipment_id: UUID, shipment_status: ShipmentStatus, workspace_id: UUID, current_user: User, db: Session) -> ShipmentResponse:
    try:
        shipment = ShipmentService(db).change_status(workspace_id, shipment_id, shipment_status, current_user.id)
    except ShipmentServiceError as exc:
        raise _bad_request(exc)
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    return shipment


@router.post("/{shipment_id}/mark-created", response_model=ShipmentResponse)
def mark_created(shipment_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> ShipmentResponse:
    return _mark_status(shipment_id, ShipmentStatus.CREATED, workspace_id, current_user, db)


@router.post("/{shipment_id}/mark-in-transit", response_model=ShipmentResponse)
def mark_in_transit(shipment_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> ShipmentResponse:
    return _mark_status(shipment_id, ShipmentStatus.IN_TRANSIT, workspace_id, current_user, db)


@router.post("/{shipment_id}/mark-arrived", response_model=ShipmentResponse)
def mark_arrived(shipment_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> ShipmentResponse:
    return _mark_status(shipment_id, ShipmentStatus.ARRIVED, workspace_id, current_user, db)


@router.post("/{shipment_id}/mark-delivered", response_model=ShipmentResponse)
def mark_delivered(shipment_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> ShipmentResponse:
    return _mark_status(shipment_id, ShipmentStatus.DELIVERED, workspace_id, current_user, db)


@router.post("/{shipment_id}/mark-returned", response_model=ShipmentResponse)
def mark_returned(shipment_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> ShipmentResponse:
    return _mark_status(shipment_id, ShipmentStatus.RETURNED, workspace_id, current_user, db)


@router.post("/{shipment_id}/cancel", response_model=ShipmentResponse)
def cancel(shipment_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> ShipmentResponse:
    shipment = ShipmentService(db).get(workspace_id, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    if shipment.nova_poshta_document_ref or shipment.nova_poshta_document_number:
        try:
            result = NovaPoshtaProviderShipmentService(db).cancel_ttn(workspace_id, shipment_id, current_user.id)
        except NovaPoshtaServiceError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        if not result.success:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.message)
        cancelled = ShipmentService(db).get(workspace_id, shipment_id)
        if cancelled is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
        return cancelled
    return _mark_status(shipment_id, ShipmentStatus.CANCELLED, workspace_id, current_user, db)


@router.post("/{shipment_id}/nova-poshta/cancel-ttn", response_model=NovaPoshtaTtnResponse)
def cancel_nova_poshta_ttn(shipment_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> NovaPoshtaTtnResponse:
    try:
        return NovaPoshtaProviderShipmentService(db).cancel_ttn(workspace_id, shipment_id, current_user.id)
    except NovaPoshtaServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{shipment_id}/nova-poshta/create-ttn", response_model=NovaPoshtaTtnResponse)
def create_nova_poshta_ttn(shipment_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> NovaPoshtaTtnResponse:
    try:
        return NovaPoshtaProviderShipmentService(db).create_ttn(workspace_id, shipment_id, current_user.id)
    except NovaPoshtaServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{shipment_id}/nova-poshta/reconcile-ttn", response_model=NovaPoshtaTtnResponse)
def reconcile_nova_poshta_ttn(shipment_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> NovaPoshtaTtnResponse:
    try:
        return NovaPoshtaProviderShipmentService(db).reconcile_ttn(workspace_id, shipment_id, current_user.id)
    except NovaPoshtaServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{shipment_id}/nova-poshta/sync-status", response_model=NovaPoshtaStatusResponse)
def sync_nova_poshta_status(shipment_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> NovaPoshtaStatusResponse:
    try:
        return NovaPoshtaProviderShipmentService(db).sync_status(workspace_id, shipment_id, current_user.id)
    except NovaPoshtaServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
