"""Recovered production auth controls, exercised only on disposable PostgreSQL."""
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.jwt import decode_token
from app.auth.session_service import SessionAuthenticationService, ConcurrentSessionRefresh
from app.auth.login_throttle import LoginThrottle, LoginThrottled
from app.core.config import get_settings
from app.database.session import engine
from app.main import app
from app.models.user import User

pytestmark = pytest.mark.skipif(
    os.getenv("SELLORA_DISPOSABLE_DATABASE") != "1" or engine.dialect.name != "postgresql",
    reason="requires explicit disposable PostgreSQL gate",
)


@pytest.fixture
def user_id():
    with Session(engine) as db:
        user = User(email=uuid4().hex + "@example.invalid", password_hash="synthetic-only",
                    first_name="QA", last_name="Synthetic")
        db.add(user); db.commit()
        return user.id


def test_cookie_rotation_concurrency_replay_and_access_revocation(user_id):
    with Session(engine) as db:
        service = SessionAuthenticationService(db)
        issued = service.create(user_id)
        sid = decode_token(issued.access_token, "access")["sid"]
        row = db.execute(text("SELECT refresh_hash FROM auth_sessions WHERE id=:sid"),
                         {"sid": sid}).first()
        assert issued.refresh_cookie not in row.refresh_hash and len(row.refresh_hash) == 64
        rotated = service.rotate(issued.refresh_cookie)
        assert rotated and rotated.refresh_cookie != issued.refresh_cookie
        with pytest.raises(ConcurrentSessionRefresh):
            service.rotate(issued.refresh_cookie)
        db.execute(text("UPDATE auth_sessions SET rotated_at=:past WHERE id=:sid"),
                   {"past": datetime.now(UTC) - timedelta(seconds=11), "sid": sid})
        db.commit()
        assert service.rotate(issued.refresh_cookie) is None
        assert service.rotate(rotated.refresh_cookie) is None
    response = TestClient(app).get("/api/v1/auth/me",
                                   headers={"Authorization": "Bearer " + rotated.access_token})
    assert response.status_code == 401


def test_logout_all_revokes_only_target_user(user_id):
    with Session(engine) as db:
        service = SessionAuthenticationService(db)
        issued = service.create(user_id)
        service.revoke_all(user_id)
        assert service.rotate(issued.refresh_cookie) is None


def test_normalized_login_throttle_retains_only_keyed_identifiers(monkeypatch):
    monkeypatch.setenv("SELLORA_LOGIN_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("SELLORA_LOGIN_RATE_LIMIT_MAX_FAILURES", "3")
    get_settings.cache_clear()
    identity = uuid4().hex + "@example.invalid"
    try:
        with Session(engine) as db:
            guard = LoginThrottle(db)
            for _ in range(3):
                guard.failed(identity.upper())
            with pytest.raises(LoginThrottled):
                guard.check(" " + identity + " ")
            key = guard._key(identity)
            assert identity not in key and len(key) == 64
            guard.succeeded(identity)
            guard.check(identity)
    finally:
        get_settings.cache_clear()


def test_recovered_schema_keeps_rls_and_refuses_destructive_downgrade():
    from alembic import command
    from alembic.config import Config
    with Session(engine) as db:
        current_head = db.scalar(text("SELECT version_num FROM alembic_version"))
        from alembic.script import ScriptDirectory
        revisions = {r.revision for r in ScriptDirectory.from_config(Config("alembic.ini")).walk_revisions()}
        assert {"202610200037", "202610200038"}.issubset(revisions)
        assert current_head == ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
        rows = db.execute(text(
            "SELECT relname,relrowsecurity FROM pg_class "
            "WHERE oid IN ('auth_sessions'::regclass,'auth_login_attempts'::regclass)"
        )).all()
        assert len(rows) == 2 and all(row.relrowsecurity for row in rows)
    with pytest.raises(RuntimeError, match="Dropping live sessions"):
        command.downgrade(Config("alembic.ini"), "202607220036")
    with Session(engine) as db:
        assert db.scalar(text("SELECT version_num FROM alembic_version")) == current_head
