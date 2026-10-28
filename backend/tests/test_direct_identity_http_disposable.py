import os
import pytest
from types import SimpleNamespace
from uuid import uuid4
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.api.v1.direct_customer_automation import router
from app.database.session import engine, get_db
from app.dependencies.auth import get_current_user
from app.dependencies.rbac import get_workspace_id
from app.models.workspace import Workspace
from app.models.user import User
from app.models.customer import Customer
from app.models.ai_direct import DirectConversation

pytestmark = pytest.mark.skipif(
    os.getenv("SELLORA_DISPOSABLE_DATABASE") != "1" or engine.dialect.name != "postgresql"
    or engine.url.host != "sellora-s2-http-db-1028",
    reason="requires the dedicated disposable S2 PostgreSQL instance",
)

def test_conflict_to_confirmed_link():
    with Session(engine) as db:
        w = Workspace(name="Synthetic QA", slug=uuid4().hex)
        other = Workspace(name="Other QA", slug=uuid4().hex)
        u = User(email=uuid4().hex+"@example.invalid", password_hash="synthetic", first_name="QA", last_name="Only")
        db.add_all([w, other, u]); db.flush()
        c = DirectConversation(workspace_id=w.id, channel="INSTAGRAM", participant_scoped_id="synthetic-new", participant_username="synthetic_buyer", participant_display_name="QA", unread_count=0, status="OPEN", priority="NORMAL", ai_processing_status="NOT_REQUESTED")
        match = Customer(workspace_id=w.id, name="Synthetic match", instagram_username="synthetic_buyer", instagram_scoped_id="synthetic-old")
        foreign = Customer(workspace_id=other.id, name="Foreign", instagram_username="synthetic_buyer")
        db.add_all([c,match,foreign]); db.commit()
        wid, uid, cid, mid, fid = w.id, u.id, c.id, match.id, foreign.id
    user = SimpleNamespace(id=uid, workspaces=[SimpleNamespace(workspace_id=wid, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name="MANAGER"))])
    app = FastAPI(); app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_workspace_id] = lambda: wid
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    client = TestClient(app)
    prefix = f"/direct/conversations/{cid}/customer-automation"
    response = client.post(prefix+"/ensure")
    assert response.status_code == 409, response.text
    with Session(engine) as db:
        assert db.get(DirectConversation, cid).linked_customer_id is None
    response = client.get(prefix+"/candidates")
    assert response.status_code == 200, response.text
    assert [x["id"] for x in response.json()] == [str(mid)]
    response = client.post(prefix+"/link", json={"customer_id": str(fid)})
    assert response.status_code == 409, response.text
    with Session(engine) as db:
        assert db.get(DirectConversation, cid).linked_customer_id is None
    response = client.post(prefix+"/link", json={"customer_id": str(mid)})
    assert response.status_code == 200, response.text
    with Session(engine) as db:
        assert db.get(DirectConversation, cid).linked_customer_id == mid
        assert db.get(Customer, mid).instagram_scoped_id == "synthetic-old"
    response = client.post(prefix+"/link", json={"customer_id": str(mid)})
    assert response.status_code == 409, response.text
