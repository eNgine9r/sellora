from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.services.customer_service import CustomerService

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
