"""Seed synthetic operator and workspace records in the existing disposable browser database."""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.auth.password import hash_password
from app.database.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.platform_admin import PlatformGrant, PlatformRole
from app.models.product_usage import UsageEvent, UsageSource
from app.models.role import Role, RoleName
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_subscription import WorkspaceSubscription
from app.models.workspace_user import WorkspaceUser
from app.repositories.audit_log_repository import DEMO_WORKSPACE_CREATE_ACTION
from app.repositories.product_usage_repository import ProductUsageRepository


def main() -> None:
    url = make_url(os.environ["DATABASE_URL"])
    if (os.getenv("SELLORA_DIRECT_CONFLICT_E2E") != "YES"
        or url.host not in ("127.0.0.1", "localhost")
        or url.database != "sellora_direct_client_conflict_e2e_isolated"):
        raise SystemExit("Platform browser fixtures require the loopback disposable browser database")

    with SessionLocal.begin() as db:
        password_hash = hash_password("QA-Platform-Local123!")
        admin = User(email="qa-platform-admin@example.com", password_hash=password_hash, first_name="QA", last_name="Admin")
        owner = User(email="qa-platform-owner@example.com", password_hash=password_hash, first_name="QA", last_name="Owner")
        now = datetime.now(UTC)
        workspaces = [
            Workspace(name=f"QA Platform Shop {index:02}", slug=f"qa-platform-shop-{index:02}",
                      is_active=index != 1, created_at=now - timedelta(minutes=22 - index))
            for index in range(1, 23)
        ]
        role = db.scalar(select(Role).where(Role.name == RoleName.OWNER))
        if role is None:
            role = Role(name=RoleName.OWNER)
        db.add_all([admin, owner, role, *workspaces])
        db.flush()
        db.add(PlatformGrant(user_id=admin.id, role=PlatformRole.ADMIN))
        db.add(WorkspaceUser(user_id=owner.id, workspace_id=workspaces[-1].id, role_id=role.id))
        db.add(AuditLog(
            workspace_id=workspaces[0].id, entity_type="Workspace", entity_id=str(workspaces[0].id),
            action=DEMO_WORKSPACE_CREATE_ACTION,
        ))
        db.add(WorkspaceSubscription(
            workspace_id=workspaces[-1].id, plan_code="qa-pilot", status="ACTIVE",
            current_period_start=now - timedelta(days=1), current_period_end=now + timedelta(days=14),
        ))
        usage = ProductUsageRepository(db)
        for workspace, occurred_at in ((workspaces[-1], now), (workspaces[-2], now - timedelta(days=12))):
            usage.record(workspace.id, UsageEvent.ORDER_CREATED, UsageSource.ORDERS, uuid4().hex, occurred_at)



if __name__ == "__main__":
    main()
