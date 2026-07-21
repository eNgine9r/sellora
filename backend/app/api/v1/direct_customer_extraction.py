from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.exceptions import AIError
from app.ai.services.direct_customer_data_extraction_service import (
    DirectCustomerDataExtractionService,
)
from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.direct_customer_extraction import (
    DirectCustomerExtractionApplyRequest,
    DirectCustomerExtractionResponse,
)
from app.services.direct_customer_automation_service import DirectCustomerAutomationError


router = APIRouter(prefix="/direct", tags=["direct-customer-extraction"])


def _http_error(exc: Exception) -> HTTPException:
    code = getattr(exc, "safe_code", str(exc))
    if code in {"DIRECT_CONVERSATION_NOT_FOUND", "DIRECT_CUSTOMER_EXTRACTION_NOT_FOUND"}:
        return HTTPException(status.HTTP_404_NOT_FOUND, code)
    if code in {
        "AI_PROVIDER_NOT_CONFIGURED",
        "AI_PROVIDER_UNAVAILABLE",
        "AI_PROVIDER_CREDENTIAL_INVALID",
        "AI_PROVIDER_FORBIDDEN",
        "AI_BILLING_QUOTA_EXCEEDED",
        "AI_REQUEST_TIMEOUT",
        "AI_RATE_LIMITED",
    }:
        return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, code)
    if code in {"DIRECT_CUSTOMER_EXTRACTION_NOT_READY"}:
        return HTTPException(status.HTTP_409_CONFLICT, code)
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, code)


@router.get(
    "/conversations/{conversation_id}/customer-data-extraction",
    response_model=DirectCustomerExtractionResponse | None,
)
def get_customer_data_extraction(
    conversation_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    _: User = Depends(require_min_role(RoleName.ANALYST)),
    db: Session = Depends(get_db),
):
    try:
        return DirectCustomerDataExtractionService(db).latest(workspace_id, conversation_id)
    except (AIError, DirectCustomerAutomationError) as exc:
        raise _http_error(exc) from exc


@router.post(
    "/conversations/{conversation_id}/customer-data-extraction/extract",
    response_model=DirectCustomerExtractionResponse,
)
async def extract_customer_data(
    conversation_id: UUID,
    workspace_id: UUID = Depends(get_workspace_id),
    user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    try:
        response = await DirectCustomerDataExtractionService(db).extract_now(
            workspace_id,
            conversation_id,
            user.id,
        )
        db.commit()
        return response
    except (AIError, DirectCustomerAutomationError) as exc:
        db.rollback()
        raise _http_error(exc) from exc


@router.post(
    "/conversations/{conversation_id}/customer-data-extraction/apply",
    response_model=DirectCustomerExtractionResponse,
)
def apply_customer_data_extraction(
    conversation_id: UUID,
    payload: DirectCustomerExtractionApplyRequest,
    workspace_id: UUID = Depends(get_workspace_id),
    user: User = Depends(require_min_role(RoleName.MANAGER)),
    db: Session = Depends(get_db),
):
    try:
        return DirectCustomerDataExtractionService(db).apply(
            workspace_id,
            conversation_id,
            payload,
            user.id,
        )
    except (AIError, DirectCustomerAutomationError) as exc:
        db.rollback()
        raise _http_error(exc) from exc
