"""Real PostgreSQL release gate. Explicit disposable DB opt-in; no provider traffic."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.database.session import engine
from app.main import app
from app.models.customer import Customer
from app.models.ai_direct import DirectConversation, DirectMessage
from app.models.lead import Lead
from app.models.meta_instagram import InstagramConnection
from app.models.role import Role
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_user import WorkspaceUser
from app.services.direct_lead_service import DirectLeadService
from app.services.direct_customer_automation_service import DirectCustomerAutomationService
from app.services.lead_service import LeadService

pytestmark = pytest.mark.skipif(
    os.getenv("SELLORA_DISPOSABLE_DATABASE") != "1" or engine.dialect.name != "postgresql",
    reason="requires explicit disposable PostgreSQL gate",
)


@pytest.fixture
def seed():
    with Session(engine) as db:
        workspace = Workspace(name="Synthetic release QA", slug="qa-" + uuid4().hex)
        foreign = Workspace(name="Synthetic foreign QA", slug="qa-" + uuid4().hex)
        db.add_all([workspace, foreign]); db.flush()
        connection = InstagramConnection(workspace_id=workspace.id, status="CONNECTED",
                                         instagram_account_id="qa-business-" + uuid4().hex)
        db.add(connection); db.flush()
        conversation = DirectConversation(workspace_id=workspace.id, channel="INSTAGRAM",
            instagram_connection_id=connection.id, participant_scoped_id="qa-buyer-" + uuid4().hex,
            participant_username="synthetic_buyer", participant_display_name="Synthetic Buyer")
        db.add(conversation); db.flush()
        db.add(DirectMessage(workspace_id=workspace.id, conversation_id=conversation.id,
            direction="INBOUND", sender_type="CUSTOMER", message_type="TEXT",
            text="Хочу замовити", provider="INSTAGRAM", is_synthetic=False,
            received_at=datetime.now(UTC)))
        db.commit()
        return workspace.id, foreign.id, connection.id, conversation.id


def test_competing_requests_create_one_lead_and_cross_workspace_is_rejected(seed):
    workspace, foreign, _, conversation = seed
    barrier = Barrier(2)
    def ensure():
        with Session(engine) as db:
            barrier.wait(timeout=5)
            lead = DirectLeadService(db).ensure_from_inbound_order_intent(workspace, conversation, "Хочу купити")
            lead_id = lead.id
            db.commit()
            return lead_id
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(lambda _: ensure(), range(2)))
    assert first == second
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Lead).where(Lead.workspace_id == workspace)) == 1
        with pytest.raises(ValueError, match="DIRECT_CONVERSATION_NOT_FOUND"):
            DirectLeadService(db).ensure_manually(foreign, conversation, uuid4())


def test_database_rejects_duplicate_active_thread_for_same_participant(seed):
    from sqlalchemy.exc import IntegrityError
    workspace, _, connection, conversation = seed
    with Session(engine) as db:
        original = db.get(DirectConversation, conversation)
        db.add(DirectConversation(workspace_id=workspace, channel="INSTAGRAM",
            instagram_connection_id=connection, participant_scoped_id=original.participant_scoped_id))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_explicit_lead_conversion_reuses_direct_prospect(seed):
    workspace, _, _, conversation = seed
    with Session(engine) as db:
        lead = DirectLeadService(db).ensure_from_inbound_order_intent(workspace, conversation, "Замовляю")
        prospect = DirectCustomerAutomationService(db).ensure_candidate(workspace, conversation, None, commit=False)
        expected = prospect.customer.id
        db.commit()
        customer = LeadService(db).convert_lead_to_customer(workspace, lead.id, None)
        assert customer.id == expected
        assert db.scalar(select(func.count()).select_from(Customer).where(Customer.workspace_id == workspace)) == 1


@pytest.mark.parametrize("role,foreign_header,expected", [
    ("OWNER", False, 200), ("MANAGER", False, 200),
    ("ANALYST", False, 403), ("OWNER", True, 403), (None, False, 401),
])
def test_http_lead_role_and_membership_enforcement(seed, role, foreign_header, expected):
    workspace, foreign, _, conversation = seed
    headers = {"X-Workspace-ID": str(foreign if foreign_header else workspace)}
    if role:
        with Session(engine) as db:
            user = User(email=uuid4().hex + "@example.invalid", password_hash="not-a-real-password",
                        first_name="QA", last_name="Synthetic")
            db.add(user); db.flush()
            role_id = db.scalar(select(Role.id).where(Role.name == role))
            if role_id is None:
                role_row = Role(name=role)
                db.add(role_row); db.flush()
                role_id = role_row.id
            db.add(WorkspaceUser(workspace_id=workspace, user_id=user.id, role_id=role_id))
            db.commit()
            from app.auth.session_service import SessionAuthenticationService
            headers["Authorization"] = "Bearer " + SessionAuthenticationService(db).create(user.id).access_token
    response = TestClient(app).post(f"/api/v1/direct/conversations/{conversation}/lead/ensure", headers=headers)
    assert response.status_code == expected
