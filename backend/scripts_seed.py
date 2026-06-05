from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.password import hash_password
from app.core.config import get_settings
from app.database.session import SessionLocal
from app.models.lead_source import LeadSource
from app.models.role import Role, RoleName
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_user import WorkspaceUser

DEFAULT_LEAD_SOURCES = ["Instagram Direct", "Instagram Ads", "Telegram", "Facebook", "Repeat Customer", "Manual"]

ROLE_DESCRIPTIONS = {
    RoleName.OWNER: "Full workspace ownership and billing administration.",
    RoleName.MANAGER: "Manage workspace operations and team workflows.",
    RoleName.ANALYST: "Read and analyze workspace data.",
}


def seed_roles(db: Session) -> dict[RoleName, Role]:
    roles: dict[RoleName, Role] = {}
    for role_name, description in ROLE_DESCRIPTIONS.items():
        role = db.execute(select(Role).where(Role.name == role_name.value)).scalar_one_or_none()
        if role is None:
            role = Role(name=role_name.value, description=description)
            db.add(role)
            db.flush()
        roles[role_name] = role
    return roles


def seed_initial_admin(db: Session, roles: dict[RoleName, Role]) -> None:
    settings = get_settings()
    workspace = db.execute(select(Workspace).where(Workspace.slug == settings.initial_workspace_slug)).scalar_one_or_none()
    if workspace is None:
        workspace = Workspace(name=settings.initial_workspace_name, slug=settings.initial_workspace_slug, subscription_plan="free")
        db.add(workspace)
        db.flush()

    user = db.execute(select(User).where(User.email == settings.initial_admin_email)).scalar_one_or_none()
    if user is None:
        user = User(
            email=settings.initial_admin_email,
            password_hash=hash_password(settings.initial_admin_password),
            first_name=settings.initial_admin_first_name,
            last_name=settings.initial_admin_last_name,
        )
        db.add(user)
        db.flush()

    membership = db.execute(
        select(WorkspaceUser).where(WorkspaceUser.workspace_id == workspace.id, WorkspaceUser.user_id == user.id)
    ).scalar_one_or_none()
    if membership is None:
        db.add(WorkspaceUser(workspace_id=workspace.id, user_id=user.id, role_id=roles[RoleName.OWNER].id))

    for source_name in DEFAULT_LEAD_SOURCES:
        lead_source = db.execute(
            select(LeadSource).where(
                LeadSource.workspace_id == workspace.id,
                LeadSource.name == source_name,
                LeadSource.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if lead_source is None:
            db.add(LeadSource(workspace_id=workspace.id, name=source_name, is_active=True))


def main() -> None:
    db = SessionLocal()
    try:
        roles = seed_roles(db)
        seed_initial_admin(db, roles)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
