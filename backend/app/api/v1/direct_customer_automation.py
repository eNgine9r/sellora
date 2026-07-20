from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.direct_customer_automation import (
    DirectCustomerAutomationState,
    DirectCustomerCompleteRequest,
    DirectCustomerFinalizeOrderRequest,
)
from app.services.direct_customer_automation_service import (
    DirectCustomerAutomationError,
    DirectCustomerAutomationService,
)
from app.services.direct_customer_order_finalization_service import (
    DirectCustomerOrderFinalizationService,
)


router = APIRouter(prefix="/direct", tags=["direct-customer-automation"])


def _http_error(exc: DirectCustomerAutomationError) -> HTTPException:
    code = str(exc)
    if code in {
        "DIRECT_CONVERSATION_NOT_FOUND",
        "DIRECT_CUSTOMER_NOT_FOUND",
        "DIRECT_ORDER_NOT_FOUND",
    }:
        return HTTPException(status.HTTP_404_NOT_FOUND, code)
    if code in {
        "DIRECT_ORDER_REQUIRED",
        "DIRECT_CUSTOMER_WORKSPACE_MISMATCH",
        "DIRECT_ORDER_CUSTOMER_MISMATCH",
    }:
        return HTTPException(status.HTTP_409_CONFLICT, code)
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, code)


@router.get(
    "/conversations/{conversation_id}/customer-automation",
    response_model=DirectCustomerAutomationState,
)
def get_direct_customer_automation(
    conversation_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    _: User = Depends(require_min_role(RoleName.ANALYST)),
    db: Session = Depends(get_db),
):
    try:
        return DirectCustomerAutomationService(db).state(workspace_id, conversation_id)
    except DirectCustomerAutomationError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/conversations/{conversation_id}/customer-automation/ensure",
    response_model=DirectCustomerAutomationState,
)
def ensure_direct_customer(
    conversation_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    try:
        return DirectCustomerAutomationService(db).ensure_candidate(
            workspace_id,
            conversation_id,
            user.id,
        )
    except DirectCustomerAutomationError as exc:
        db.rollback()
        raise _http_error(exc) from exc


@router.post(
    "/conversations/{conversation_id}/customer-automation/complete",
    response_model=DirectCustomerAutomationState,
)
def complete_direct_customer(
    conversation_id: UUID,
    payload: DirectCustomerCompleteRequest,
    workspace_id: UUID = Depends(get_workspace_id),
    user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    try:
        return DirectCustomerAutomationService(db).complete_after_order(
            workspace_id,
            conversation_id,
            payload,
            user.id,
        )
    except DirectCustomerAutomationError as exc:
        db.rollback()
        raise _http_error(exc) from exc


@router.post(
    "/conversations/{conversation_id}/customer-automation/finalize-order",
    response_model=DirectCustomerAutomationState,
)
def finalize_direct_customer_order(
    conversation_id: UUID,
    payload: DirectCustomerFinalizeOrderRequest,
    workspace_id: UUID = Depends(get_workspace_id),
    user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    try:
        return DirectCustomerOrderFinalizationService(db).finalize(
            workspace_id,
            conversation_id,
            payload,
            user.id,
        )
    except DirectCustomerAutomationError as exc:
        db.rollback()
        raise _http_error(exc) from exc
