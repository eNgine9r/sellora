from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.schemas.crm_completion import CustomerAddressCreate, CustomerAddressResponse, CustomerAddressUpdate, CustomerNoteCreate, CustomerNoteResponse, CustomerTagResponse
from app.services.customer_service import CustomerService
from app.services.crm_completion_service import CustomerCrmService, CrmCompletionServiceError

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=list[CustomerResponse], dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def list_customers(
    workspace_id: UUID = Depends(get_workspace_id),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CustomerResponse]:
    return CustomerService(db).list(workspace_id, search)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> CustomerResponse:
    return CustomerService(db).create(workspace_id, payload, current_user.id)


@router.get("/{customer_id}", response_model=CustomerResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def get_customer(
    customer_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    db: Session = Depends(get_db),
) -> CustomerResponse:
    customer = CustomerService(db).get(workspace_id, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> CustomerResponse:
    customer = CustomerService(db).update(workspace_id, customer_id, payload, current_user.id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
) -> Response:
    deleted = CustomerService(db).delete(workspace_id, customer_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{customer_id}/tags", response_model=list[CustomerTagResponse], dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def list_customer_tags(customer_id: UUID, workspace_id: UUID = Depends(get_workspace_id), db: Session = Depends(get_db)) -> list[CustomerTagResponse]:
    try:
        return CustomerCrmService(db).list_customer_tags(workspace_id, customer_id)
    except CrmCompletionServiceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{customer_id}/tags/{tag_id}", response_model=CustomerTagResponse, status_code=status.HTTP_201_CREATED)
def add_customer_tag(customer_id: UUID, tag_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> CustomerTagResponse:
    try:
        return CustomerCrmService(db).add_customer_tag(workspace_id, customer_id, tag_id, current_user.id)
    except CrmCompletionServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/{customer_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_customer_tag(customer_id: UUID, tag_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> Response:
    if not CustomerCrmService(db).remove_customer_tag(workspace_id, customer_id, tag_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer tag not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{customer_id}/notes", response_model=list[CustomerNoteResponse], dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def list_customer_notes(customer_id: UUID, workspace_id: UUID = Depends(get_workspace_id), db: Session = Depends(get_db)) -> list[CustomerNoteResponse]:
    try:
        return CustomerCrmService(db).list_notes(workspace_id, customer_id)
    except CrmCompletionServiceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{customer_id}/notes", response_model=CustomerNoteResponse, status_code=status.HTTP_201_CREATED)
def add_customer_note(customer_id: UUID, payload: CustomerNoteCreate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> CustomerNoteResponse:
    try:
        return CustomerCrmService(db).add_note(workspace_id, customer_id, payload, current_user.id)
    except CrmCompletionServiceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/{customer_id}/addresses", response_model=list[CustomerAddressResponse], dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def list_customer_addresses(customer_id: UUID, workspace_id: UUID = Depends(get_workspace_id), db: Session = Depends(get_db)) -> list[CustomerAddressResponse]:
    try:
        return CustomerCrmService(db).list_addresses(workspace_id, customer_id)
    except CrmCompletionServiceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{customer_id}/addresses", response_model=CustomerAddressResponse, status_code=status.HTTP_201_CREATED)
def add_customer_address(customer_id: UUID, payload: CustomerAddressCreate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> CustomerAddressResponse:
    try:
        return CustomerCrmService(db).add_address(workspace_id, customer_id, payload, current_user.id)
    except CrmCompletionServiceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.put("/{customer_id}/addresses/{address_id}", response_model=CustomerAddressResponse)
def update_customer_address(customer_id: UUID, address_id: UUID, payload: CustomerAddressUpdate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> CustomerAddressResponse:
    address = CustomerCrmService(db).update_address(workspace_id, customer_id, address_id, payload, current_user.id)
    if address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer address not found")
    return address


@router.delete("/{customer_id}/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer_address(customer_id: UUID, address_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> Response:
    if not CustomerCrmService(db).delete_address(workspace_id, customer_id, address_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer address not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
