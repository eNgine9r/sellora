import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.password import verify_password
from app.models.platform_admin import PlatformAuditEvent, PlatformGrant, PlatformRole
from app.repositories.platform_admin_repository import PlatformAuditRepository, PlatformGrantRepository
from app.repositories.user_repository import UserRepository


class PlatformGrantService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.grants = PlatformGrantRepository(db)
        self.audit = PlatformAuditRepository(db)

    def change(
        self, *, actor_id: UUID, password: str, target_id: UUID, action: str,
        approval_ref: str, role: PlatformRole | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,63}", approval_ref):
            raise ValueError("An approval reference is required")
        if action not in ("BOOTSTRAP", "GRANT", "REVOKE"):
            raise ValueError("Invalid grant operation")
        actor = self.users.get_by_id(actor_id)
        if actor is None or not actor.is_active or not verify_password(password, actor.password_hash):
            raise PermissionError("Platform operator authentication failed")
        self.grants.lock_changes()
        self.db.refresh(actor)
        if not actor.is_active:
            raise PermissionError("Platform operator is inactive")
        target = self.users.get_by_id(target_id)
        if target is None or (action != "REVOKE" and not target.is_active):
            raise ValueError("Eligible target account required")

        actor_role = None
        if action == "BOOTSTRAP":
            if actor_id != target_id or self.audit.has_bootstrap():
                raise PermissionError("Bootstrap is unavailable")
            role = PlatformRole.ADMIN
        else:
            actor_grant = self.grants.get(actor_id)
            if (
                actor_grant is None or actor_grant.revoked_at is not None
                or actor_grant.role != PlatformRole.ADMIN or actor_id == target_id
            ):
                raise PermissionError("An active platform admin must manage another operator")
            actor_role = PlatformRole.ADMIN

        grant = self.grants.get(target_id)
        now = datetime.now(UTC)
        if action == "REVOKE":
            if grant is None or grant.revoked_at is not None:
                raise ValueError("Active platform grant required")
            grant.revoked_at = now
            role = PlatformRole(grant.role)
        else:
            if role is None:
                raise ValueError("A platform role is required")
            if grant is None:
                self.grants.add(PlatformGrant(user_id=target_id, role=role, granted_at=now))
            else:
                grant.role = role
                grant.granted_at = now
                grant.revoked_at = None

        self.audit.add(PlatformAuditEvent(
            actor_user_id=actor_id, actor_role=actor_role, action=action, outcome="ALLOWED",
            target_user_id=target_id, target_role=role, approval_ref=approval_ref,
        ))
        self.db.commit()
