from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.user import User
from app.models.workspace_user import WorkspaceUser


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email).options(selectinload(User.workspaces).selectinload(WorkspaceUser.role), selectinload(User.workspaces).selectinload(WorkspaceUser.workspace))
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_id(self, user_id: UUID) -> User | None:
        stmt = select(User).where(User.id == user_id).options(selectinload(User.workspaces).selectinload(WorkspaceUser.role), selectinload(User.workspaces).selectinload(WorkspaceUser.workspace))
        return self.db.execute(stmt).scalar_one_or_none()

    def get_for_sign_in(self, email: str) -> User | None:
        exact = self.get_by_email(email)
        if exact is not None:
            return exact
        matches = self.db.scalars(select(User).where(func.lower(User.email) == email.lower()).limit(2)).all()
        return matches[0] if len(matches) == 1 else None

    def email_exists(self, email: str) -> bool:
        return self.db.scalar(select(User.id).where(func.lower(User.email) == email).limit(1)) is not None

    def create(self, *, email: str, password_hash: str | None, first_name: str, last_name: str) -> User:
        user = User(email=email, password_hash=password_hash, first_name=first_name, last_name=last_name, is_active=True)
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user
