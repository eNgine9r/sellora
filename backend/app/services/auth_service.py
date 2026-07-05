from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.password import verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import CurrentUserResponse, TokenPair, WorkspaceMembership


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def authenticate(self, email: str, password: str) -> TokenPair | None:
        user = self.users.get_by_email(email)
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            return None
        user.last_login_at = datetime.now(UTC)
        self.db.commit()
        return self.issue_tokens(user)

    def issue_tokens(self, user: User) -> TokenPair:
        return TokenPair(access_token=create_access_token(user.id), refresh_token=create_refresh_token(user.id))

    def refresh(self, refresh_token: str) -> TokenPair | None:
        try:
            payload = decode_token(refresh_token, "refresh")
            user_id = UUID(payload["sub"])
        except (KeyError, TypeError, ValueError):
            return None
        user = self.users.get_by_id(user_id)
        if not user or not user.is_active:
            return None
        return self.issue_tokens(user)

    @staticmethod
    def to_current_user_response(user: User) -> CurrentUserResponse:
        return CurrentUserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            last_login_at=user.last_login_at,
            memberships=[
                WorkspaceMembership(
                    workspace_id=membership.workspace_id,
                    workspace_name=membership.workspace.name,
                    workspace_slug=membership.workspace.slug,
                    role=membership.role.name,
                    currency_code=getattr(membership.workspace, "currency_code", "UAH"),
                )
                for membership in user.workspaces
                if membership.workspace.is_active and getattr(membership, "is_active", True)
            ],
        )
