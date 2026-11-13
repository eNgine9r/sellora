from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db
from app.dependencies.auth import authenticate_access_session, bearer_scheme
from app.models.platform_admin import PlatformRole
from app.repositories.platform_admin_repository import PlatformGrantRepository
from app.schemas.platform_admin import PlatformIdentity
from app.services.platform_admin_service import CAPABILITIES, PlatformAuditService, platform_identity
from app.services.platform_mfa_service import MFA_HEADER, PlatformMfaError, PlatformMfaService


@dataclass(frozen=True)
class PlatformSession:
    identity: PlatformIdentity
    session_id: UUID
    granted_at: datetime


def _platform_session(
    credentials: HTTPAuthorizationCredentials | None, db: Session, capability: str, action: str,
) -> PlatformSession:
    if not get_settings().platform_admin_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    user, session_id = authenticate_access_session(credentials, db, require_password_session=True)
    grant = PlatformGrantRepository(db).get(user.id)
    role = PlatformRole(grant.role) if grant is not None and grant.revoked_at is None else None
    if grant is None or role is None or capability not in CAPABILITIES[role]:
        PlatformAuditService(db).record_read(user.id, role, action, "DENIED")
        raise HTTPException(status_code=403, detail="Platform access denied")
    if session_id is None:
        raise HTTPException(status_code=401, detail="Session-bound access required")
    return PlatformSession(platform_identity(user.id, role), session_id, grant.granted_at)


def require_platform_permission(capability: str, action: str) -> Callable:
    def guard(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        db: Session = Depends(get_db),
    ) -> PlatformIdentity:
        try:
            operator = _platform_session(credentials, db, capability, action)
            if get_settings().platform_admin_requires_mfa:
                PlatformMfaService(db).check(
                    operator.identity.operator_id, operator.session_id, request.headers.get(MFA_HEADER)
                )
            return operator.identity
        except PlatformMfaError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.code) from None
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(status_code=503, detail="Platform access unavailable") from exc

    guard.platform_capability = capability
    return guard


def require_platform_mfa_challenge(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> PlatformSession:
    if not get_settings().platform_admin_requires_mfa:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        return _platform_session(credentials, db, "platform.access", "VERIFY_PLATFORM_MFA")
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Platform access unavailable") from exc
