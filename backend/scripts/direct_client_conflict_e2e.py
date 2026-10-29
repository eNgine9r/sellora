"""Seed/inspect synthetic Direct browser E2E data in an empty local canary DB only.

This CLI is never mounted in FastAPI and does not bypass authentication. The browser
logs in normally; verification opens a separate connection to inspect committed data.
"""
import argparse
import json
import os
import secrets
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.auth.password import hash_password
from app.models.ai_direct import DirectConversation, DirectMessage
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.order import Order
from app.models.role import Role
from app.models.shipment import Shipment
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_user import WorkspaceUser

DATABASE_NAME = "sellora_direct_client_conflict_e2e_isolated"
DISABLED_FEATURES = (
    "META_INSTAGRAM_WEBHOOK_WORKER_ENABLED", "META_INSTAGRAM_WEBHOOK_PROCESSING_ENABLED",
    "META_INSTAGRAM_SEND_ENABLED", "META_INSTAGRAM_AUTO_ANALYSIS_ENABLED", "META_INSTAGRAM_AUTO_SEND_ENABLED",
    "META_SYNC_ENABLED", "AI_FEATURE_ENABLED", "AI_CUSTOMER_DATA_EXTRACTION_ENABLED",
    "STAGING_NOVA_POSHTA_ALLOW_WRITES",
)


def require_disposable_target(environment):
    if environment.get("SELLORA_DIRECT_CONFLICT_E2E") != "YES":
        raise RuntimeError("Explicit disposable Direct E2E opt-in required")
    url = make_url(environment.get("DATABASE_URL", ""))
    if url.get_backend_name() != "postgresql" or url.database != DATABASE_NAME or url.host not in {"127.0.0.1", "localhost", "::1"} or url.query:
        raise RuntimeError("Expected the exact loopback disposable PostgreSQL database")
    if any(environment.get(name) != "false" for name in DISABLED_FEATURES):
        raise RuntimeError("External processing, AI and provider writes must be disabled")
    return url


def _snapshot(record):
    return {column.name: str(getattr(record, column.name)) if getattr(record, column.name) is not None else None
            for column in record.__table__.columns}


def seed(db):
    db.execute(text("SET LOCAL lock_timeout = '3s'"))
    db.execute(text("LOCK TABLE workspaces, users IN EXCLUSIVE MODE"))
    for model in (Workspace, User, Customer, DirectConversation):
        if db.scalar(select(func.count()).select_from(model)):
            raise RuntimeError("Disposable database must contain no application data")
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    if db.scalar(text("SELECT version_num FROM alembic_version")) != ScriptDirectory.from_config(Config("alembic.ini")).get_current_head():
        raise RuntimeError("Disposable database must be migrated to the current head")
    first = Workspace(name="Synthetic Direct E2E", slug="synthetic-direct-e2e")
    foreign = Workspace(name="Synthetic other tenant E2E", slug="synthetic-other-direct-e2e")
    password = secrets.token_urlsafe(24)
    users = [User(email=f"direct-e2e-{name}@example.com", password_hash=hash_password(password),
                  first_name="Synthetic", last_name=name) for name in ("manager", "foreign")]
    db.add_all([first, foreign, *users])
    db.flush()
    role = db.scalar(select(Role).where(Role.name == "MANAGER"))
    if role is None:
        role = Role(name="MANAGER")
        db.add(role)
        db.flush()
    for workspace, user in zip((first, foreign), users):
        db.add(WorkspaceUser(workspace_id=workspace.id, user_id=user.id, role_id=role.id))
    cases, snapshots = {}, {}
    for viewport in ("desktop", "mobile"):
        for action in ("confirm", "cancel", "denial"):
            key = f"{viewport}-{action}"
            username = key.replace("-", "_")
            candidates = [Customer(workspace_id=first.id, name=f"Synthetic {key} {choice}", instagram_username=username)
                          for choice in ("alternative", "selected")]
            other = Customer(workspace_id=foreign.id, name=f"Foreign synthetic {key}", instagram_username=username)
            conversations = [DirectConversation(workspace_id=workspace.id, channel="SYNTHETIC",
                             participant_username=username, participant_display_name=f"Synthetic {key} dialog",
                             participant_scoped_id=f"synthetic-{key}", unread_count=0)
                             for workspace in (first, foreign)]
            db.add_all([*candidates, other, *conversations])
            db.flush()
            for record in [*candidates, other, *conversations]:
                db.refresh(record)
            cases[key] = {
                "conversation_id": str(conversations[0].id),
                "display_name": conversations[0].participant_display_name,
                "candidate_ids": [str(customer.id) for customer in candidates],
                "candidate_names": [customer.name for customer in candidates],
                "foreign_customer_id": str(other.id), "foreign_customer_name": other.name,
                "foreign_conversation_id": str(conversations[1].id),
                "conversation_snapshot": _snapshot(conversations[0]),
                "foreign_conversation_snapshot": _snapshot(conversations[1]),
            }
            snapshots.update({str(customer.id): _snapshot(customer) for customer in [*candidates, other]})
    return {"version": 1, "workspace_id": str(first.id), "foreign_workspace_id": str(foreign.id),
            "user_id": str(users[0].id), "login": {"email": users[0].email, "password": password},
            "cases": cases, "customer_snapshots": snapshots}


def verify(db, manifest, case_name, expected):
    if manifest["version"] != 1:
        raise RuntimeError("Unsupported synthetic fixture manifest")
    case = manifest["cases"][case_name]
    workspace_id, foreign_id = UUID(manifest["workspace_id"]), UUID(manifest["foreign_workspace_id"])
    conversation = db.scalar(select(DirectConversation).where(
        DirectConversation.workspace_id == workspace_id, DirectConversation.id == UUID(case["conversation_id"])))
    foreign_conversation = db.scalar(select(DirectConversation).where(
        DirectConversation.workspace_id == foreign_id, DirectConversation.id == UUID(case["foreign_conversation_id"])))
    expected_customer = UUID(case["candidate_ids"][1]) if expected == "confirmed" else None
    assert conversation.linked_customer_id == expected_customer, "Unexpected persisted customer binding"
    expected_conversation = dict(case["conversation_snapshot"])
    if expected == "confirmed":
        expected_conversation.update(linked_customer_id=str(expected_customer), updated_at=str(conversation.updated_at))
    assert _snapshot(conversation) == expected_conversation, "Unexpected persisted conversation change"
    assert _snapshot(foreign_conversation) == case["foreign_conversation_snapshot"], "Foreign conversation was changed"
    audits = list(db.scalars(select(AuditLog).where(
        AuditLog.workspace_id == workspace_id, AuditLog.entity_id == case["conversation_id"],
        AuditLog.action == "DIRECT_CUSTOMER_LINK")))
    assert len(audits) == (1 if expected == "confirmed" else 0), "Unexpected persisted identity audit"
    if audits:
        assert audits[0].user_id == UUID(manifest["user_id"])
        assert audits[0].new_value == {"customer_id": str(expected_customer), "automatic": False, "identity_reviewed": True}
    customers = list(db.scalars(select(Customer).where(Customer.workspace_id.in_([workspace_id, foreign_id]))))
    assert {str(customer.id): _snapshot(customer) for customer in customers} == manifest["customer_snapshots"], "Customer records were mutated"
    for model in (DirectMessage, Lead, Order, Shipment):
        assert db.scalar(select(func.count()).select_from(model).where(model.workspace_id.in_([workspace_id, foreign_id]))) == 0, "Unexpected messages, leads, orders or shipments"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seed", "verify"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--case")
    parser.add_argument("--expected", choices=("unbound", "confirmed"))
    args = parser.parse_args()
    url = require_disposable_target(os.environ)
    engine = create_engine(url)
    try:
        with Session(engine) as db:
            if args.action == "seed":
                if args.manifest.exists():
                    raise RuntimeError("Refusing to overwrite an existing fixture manifest")
                data = seed(db)
                descriptor = os.open(args.manifest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                    json.dump(data, output)
                try:
                    db.commit()
                except Exception:
                    args.manifest.unlink()
                    raise
            else:
                if not args.case or not args.expected:
                    parser.error("verify requires --case and --expected")
                verify(db, json.loads(args.manifest.read_text()), args.case, args.expected)
        print("PASS synthetic Direct fixture " + args.action)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
