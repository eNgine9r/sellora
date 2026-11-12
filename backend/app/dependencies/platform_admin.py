from collections.abc import Callable

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db
from app.dependencies.auth import authenticate_access, bearer_scheme
from app.models.platform_admin import PlatformRole
from app.repositories.platform_admin_repository import PlatformGrantRepository
from app.schemas.platform_admin import PlatformIdentity
from app.services.platform_admin_service import CAPABILITIES, PlatformAuditService, platform_identity


def require_platform_permission(capability: str, action: str) -> Callable:
    def guard(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        db: Session = Depends(get_db),
    ) -> PlatformIdentity:
        if not get_settings().platform_admin_enabled:
            raise HTTPException(status_code=404, detail="Not found")
        try:
            user = authenticate_access(credentials, db, require_password_session=True)
            grant = PlatformGrantRepository(db).get(user.id)
            role = PlatformRole(grant.role) if grant is not None and grant.revoked_at is None else None
            if role is None or capability not in CAPABILITIES[role]:
                PlatformAuditService(db).record_read(user.id, role, action, "DENIED")
                raise HTTPException(status_code=403, detail="Platform access denied")
            return platform_identity(user.id, role)
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(status_code=503, detail="Platform access unavailable") from exc

    guard.platform_capability = capability
    return guard
