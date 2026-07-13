from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.role import Role, RoleName
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_user import WorkspaceUser


class WorkspaceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_role(self, role: RoleName) -> Role | None:
        return self.db.execute(select(Role).where(Role.name == role.value)).scalar_one_or_none()

    def list_for_user(self, user_id: UUID) -> list[WorkspaceUser]:
        stmt = (
            select(WorkspaceUser)
            .join(WorkspaceUser.workspace)
            .where(WorkspaceUser.user_id == user_id, WorkspaceUser.is_active.is_(True), Workspace.is_active.is_(True))
            .options(selectinload(WorkspaceUser.workspace), selectinload(WorkspaceUser.role))
            .order_by(Workspace.created_at.asc(), Workspace.name.asc())
        )
        return list(self.db.execute(stmt).scalars())

    def get_membership(self, workspace_id: UUID, user_id: UUID) -> WorkspaceUser | None:
        stmt = select(WorkspaceUser).where(WorkspaceUser.workspace_id == workspace_id, WorkspaceUser.user_id == user_id).options(selectinload(WorkspaceUser.user), selectinload(WorkspaceUser.role), selectinload(WorkspaceUser.workspace))
        return self.db.execute(stmt).scalar_one_or_none()

    def get_active_membership(self, workspace_id: UUID, user_id: UUID) -> WorkspaceUser | None:
        membership = self.get_membership(workspace_id, user_id)
        if membership and membership.is_active and membership.workspace.is_active:
            return membership
        return None


    def find_active_demo_for_user(self, user_id: UUID) -> WorkspaceUser | None:
        stmt = (
            select(WorkspaceUser)
            .join(WorkspaceUser.workspace)
            .where(
                WorkspaceUser.user_id == user_id,
                WorkspaceUser.is_active.is_(True),
                Workspace.is_active.is_(True),
                Workspace.slug.like("demo-sellora-%"),
            )
            .options(selectinload(WorkspaceUser.workspace), selectinload(WorkspaceUser.role))
            .order_by(Workspace.created_at.asc())
        )
        return self.db.execute(stmt).scalars().first()

    def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        return self.db.get(Workspace, workspace_id)

    def get_by_slug(self, slug: str) -> Workspace | None:
        return self.db.execute(select(Workspace).where(Workspace.slug == slug)).scalar_one_or_none()

    def create_workspace(self, *, name: str, slug: str, currency_code: str, timezone: str) -> Workspace:
        workspace = Workspace(name=name, slug=slug, currency_code=currency_code, timezone=timezone, is_active=True)
        self.db.add(workspace)
        self.db.flush()
        return workspace

    def add_membership(self, *, workspace_id: UUID, user_id: UUID, role: RoleName) -> WorkspaceUser:
        role_model = self.get_role(role)
        if role_model is None:
            raise ValueError(f"Role {role.value} is not configured")
        membership = WorkspaceUser(workspace_id=workspace_id, user_id=user_id, role_id=role_model.id, is_active=True)
        self.db.add(membership)
        self.db.flush()
        self.db.refresh(membership)
        return membership

    def list_members(self, workspace_id: UUID) -> list[WorkspaceUser]:
        stmt = select(WorkspaceUser).where(WorkspaceUser.workspace_id == workspace_id).options(selectinload(WorkspaceUser.user), selectinload(WorkspaceUser.role)).order_by(WorkspaceUser.created_at.asc())
        return list(self.db.execute(stmt).scalars())

    def count_active_owners(self, workspace_id: UUID) -> int:
        stmt = select(func.count()).select_from(WorkspaceUser).join(WorkspaceUser.role).where(WorkspaceUser.workspace_id == workspace_id, WorkspaceUser.is_active.is_(True), Role.name == RoleName.OWNER.value)
        return int(self.db.execute(stmt).scalar_one())
