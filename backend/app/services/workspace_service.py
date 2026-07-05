from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.password import hash_password
from app.models.role import RoleName
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_user import WorkspaceUser
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import WorkspaceCreate, WorkspaceSettingsUpdate, WorkspaceUserCreate
from app.services.business_utils import snapshot

DUPLICATE_USER_MESSAGE = "Користувач уже доданий до команди."
LAST_OWNER_ROLE_MESSAGE = "Неможливо змінити роль останнього власника робочого простору."
LAST_OWNER_DEACTIVATE_MESSAGE = "Неможливо деактивувати останнього власника робочого простору."


class WorkspaceValidationError(ValueError):
    pass


class WorkspacePermissionError(PermissionError):
    pass


class WorkspaceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit_logs = AuditLogRepository(db)
        self.workspaces = WorkspaceRepository(db)
        self.users = UserRepository(db)

    def list_available_workspaces(self, user_id: UUID) -> list[WorkspaceUser]:
        return self.workspaces.list_for_user(user_id)

    def create_workspace(self, payload: WorkspaceCreate, actor_user_id: UUID) -> WorkspaceUser:
        if self.workspaces.get_by_slug(payload.slug):
            raise WorkspaceValidationError("Workspace slug already exists")
        try:
            workspace = self.workspaces.create_workspace(name=payload.name.strip(), slug=payload.slug, currency_code=payload.currency_code.value, timezone=payload.timezone)
            membership = self.workspaces.add_membership(workspace_id=workspace.id, user_id=actor_user_id, role=RoleName.OWNER)
            self.db.commit()
            return membership
        except Exception:
            self.db.rollback()
            raise

    def get_settings(self, workspace_id: UUID) -> Workspace | None:
        if hasattr(self, "workspaces"):
            return self.workspaces.get_workspace(workspace_id)
        return self.db.get(Workspace, workspace_id)

    def get_current_workspace(self, workspace_id: UUID, actor_user_id: UUID) -> WorkspaceUser | None:
        return self.workspaces.get_active_membership(workspace_id, actor_user_id)

    def require_owner(self, workspace_id: UUID, actor_user_id: UUID) -> WorkspaceUser:
        membership = self.workspaces.get_active_membership(workspace_id, actor_user_id)
        if membership is None or membership.role.name != RoleName.OWNER.value:
            raise WorkspacePermissionError("Insufficient workspace permissions")
        return membership

    def update_settings(self, workspace_id: UUID, payload: WorkspaceSettingsUpdate, actor_user_id: UUID | None) -> Workspace | None:
        if actor_user_id is not None and hasattr(self, "workspaces"):
            self.require_owner(workspace_id, actor_user_id)
        workspace = self.get_settings(workspace_id)
        if workspace is None or not workspace.is_active:
            return None
        changes = payload.model_dump(exclude_unset=True)
        if "slug" in changes and changes["slug"] is not None:
            existing = self.workspaces.get_by_slug(changes["slug"]) if hasattr(self, "workspaces") else None
            if existing and existing.id != workspace_id:
                raise WorkspaceValidationError("Workspace slug already exists")
        old_value = snapshot(workspace)
        currency_changed = "currency_code" in changes and changes["currency_code"] is not None and changes["currency_code"].value != workspace.currency_code
        if "name" in changes and changes["name"] is not None:
            workspace.name = changes["name"].strip()
        if "slug" in changes and changes["slug"] is not None:
            workspace.slug = changes["slug"]
        if "currency_code" in changes and changes["currency_code"] is not None:
            workspace.currency_code = changes["currency_code"].value
        if "timezone" in changes and changes["timezone"] is not None:
            workspace.timezone = changes["timezone"]
        action = "WORKSPACE_CURRENCY_UPDATE" if currency_changed else "WORKSPACE_UPDATE"
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="Workspace", entity_id=workspace.id, action=action, old_value=old_value, new_value=snapshot(workspace))
        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def list_workspace_users(self, workspace_id: UUID, actor_user_id: UUID) -> list[WorkspaceUser]:
        self.require_owner(workspace_id, actor_user_id)
        return self.workspaces.list_members(workspace_id)

    def add_workspace_user(self, workspace_id: UUID, payload: WorkspaceUserCreate, actor_user_id: UUID) -> WorkspaceUser:
        self.require_owner(workspace_id, actor_user_id)
        user = self.users.get_by_email(payload.email)
        if user is not None and self.workspaces.get_membership(workspace_id, user.id) is not None:
            raise WorkspaceValidationError(DUPLICATE_USER_MESSAGE)
        try:
            if user is None:
                parts = payload.full_name.strip().split(maxsplit=1)
                user = self.users.create(email=payload.email, password_hash=hash_password(payload.temporary_password), first_name=parts[0], last_name=parts[1] if len(parts) > 1 else "")
            membership = self.workspaces.add_membership(workspace_id=workspace_id, user_id=user.id, role=payload.role)
            self.db.commit()
            return membership
        except IntegrityError as exc:
            self.db.rollback()
            raise WorkspaceValidationError(DUPLICATE_USER_MESSAGE) from exc
        except Exception:
            self.db.rollback()
            raise

    def change_user_role(self, workspace_id: UUID, target_user_id: UUID, role: RoleName, actor_user_id: UUID) -> WorkspaceUser:
        self.require_owner(workspace_id, actor_user_id)
        membership = self.workspaces.get_active_membership(workspace_id, target_user_id)
        if membership is None:
            raise WorkspaceValidationError("Workspace user not found")
        if membership.role.name == RoleName.OWNER.value and role != RoleName.OWNER and self.workspaces.count_active_owners(workspace_id) <= 1:
            raise WorkspaceValidationError(LAST_OWNER_ROLE_MESSAGE)
        role_model = self.workspaces.get_role(role)
        if role_model is None:
            raise WorkspaceValidationError("Role not found")
        membership.role_id = role_model.id
        self.db.commit()
        self.db.refresh(membership)
        return membership

    def deactivate_user(self, workspace_id: UUID, target_user_id: UUID, actor_user_id: UUID) -> WorkspaceUser:
        self.require_owner(workspace_id, actor_user_id)
        membership = self.workspaces.get_active_membership(workspace_id, target_user_id)
        if membership is None:
            raise WorkspaceValidationError("Workspace user not found")
        if membership.role.name == RoleName.OWNER.value and self.workspaces.count_active_owners(workspace_id) <= 1:
            raise WorkspaceValidationError(LAST_OWNER_DEACTIVATE_MESSAGE)
        membership.is_active = False
        self.db.commit()
        self.db.refresh(membership)
        return membership
