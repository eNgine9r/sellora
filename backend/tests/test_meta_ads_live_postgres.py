"""Real DB durability/concurrency tests. No provider or production access."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

from app.api.v1.meta_ads import router
from app.core.config import Settings
from app.database.session import engine, get_db
from app.dependencies.auth import get_current_user
from app.dependencies.rbac import get_workspace_id
from app.integrations.meta_ads.live_oauth_client import MetaTokenExchangeResult
from app.integrations.meta_ads.schemas import MetaAdAccountDTO, MetaCampaignDTO, MetaInsightsRowDTO
from app.models.ad_campaign import AdCampaign
from app.models.ad_metric import AdMetric
from app.models.audit_log import AuditLog
from app.models.meta_ad_connection import MetaAdConnection
from app.models.meta_ads_oauth_state import MetaAdsOAuthState
from app.models.user import User
from app.models.workspace import Workspace
from app.services.meta_ads_connection_service import MetaAdsConnectionService, MetaAdsConnectionServiceError
from app.services.meta_ads_live_sync_service import MetaAdsLiveSyncService

pytestmark = pytest.mark.skipif(os.getenv("SELLORA_DISPOSABLE_DATABASE") != "1" or engine.dialect.name != "postgresql",
    reason="requires explicitly disposable PostgreSQL")

DAY = date(2026, 10, 1)
TOKEN = "synthetic-only-private-token"


class Exchange:
    calls = 0
    def exchange_code_for_token(self, **kwargs):
        self.calls += 1
        return MetaTokenExchangeResult(TOKEN, datetime.now(UTC) + timedelta(hours=1), ("ads_read",))


class Reader:
    hook = None
    def __init__(self, **kwargs):
        assert kwargs["access_token"] == TOKEN
    def list_ad_accounts(self):
        return [MetaAdAccountDTO("act_123", "Synthetic UAH", "UAH", "Europe/Kyiv"),
                MetaAdAccountDTO("act_456", "Synthetic USD", "USD", "UTC"),
                MetaAdAccountDTO("act_789", "Other UAH", "UAH", "UTC")]
    def list_campaigns(self, account):
        assert account in {"act_123", "act_789"}
        return [MetaCampaignDTO("12345", account, "Synthetic campaign", "ACTIVE", "OUTCOME_SALES", "META", datetime.now(UTC))]
    def get_campaign_insights_preview(self, account, start, end):
        if self.hook:
            self.hook()
        return [MetaInsightsRowDTO("12345", DAY, "12.30", 100, 5, 2, currency="UAH")]


@pytest.fixture
def fixture():
    with Session(engine) as db:
        w = Workspace(name="Ads QA", slug=uuid4().hex)
        u = User(email=uuid4().hex + "@example.invalid", password_hash="synthetic", first_name="QA", last_name="Only")
        db.add_all([w, u]); db.commit()
        ids = w.id, u.id
    settings = Settings(_env_file=None, meta_connections_enabled=True, meta_live_oauth_enabled=True,
        meta_token_storage_enabled=True, meta_sync_enabled=True, meta_ads_app_id="123",
        meta_ads_app_secret="synthetic-only", meta_token_encryption_key=Fernet.generate_key().decode(),
        meta_ads_oauth_redirect_uri="https://backend.example.invalid/api/v1/integrations/meta-ads/oauth/callback",
        meta_ads_oauth_frontend_callback_url="https://frontend.example.invalid/settings/integrations/meta-ads/callback")
    return (*ids, settings)


def connect(fixture):
    wid, uid, settings = fixture
    with Session(engine) as db:
        service = MetaAdsConnectionService(db, settings=settings, token_exchange_client=Exchange())
        start = service.start_oauth(wid, uid)
        state = parse_qs(urlparse(start.authorization_url).query)["state"][0]
        result = service.complete_callback(wid, uid, state=state, code="synthetic-code")
        assert result.connected and result.account_selection_required
        assert TOKEN not in result.model_dump_json()
        assert result.token_fingerprint is None
    return state


def select_account(fixture, identifier="act_123"):
    wid, uid, settings = fixture
    with Session(engine) as db:
        return MetaAdsLiveSyncService(db, settings=settings, reader_factory=Reader).select_account(wid, uid, identifier)


def sync(fixture, reader=Reader):
    wid, uid, settings = fixture
    with Session(engine) as db:
        return MetaAdsLiveSyncService(db, settings=settings, reader_factory=reader).sync(wid, uid, DAY, DAY)


def test_state_replay_cross_user_workspace_tamper_and_restart(fixture):
    wid, uid, settings = fixture
    with Session(engine) as db:
        start = MetaAdsConnectionService(db, settings=settings).start_oauth(wid, uid)
    state = parse_qs(urlparse(start.authorization_url).query)["state"][0]
    # Each attempt uses a new DB Session/service (restart-safe persistence).
    for attempt_w, attempt_u, value in [(wid, uuid4(), state), (wid, uid, state[:-1] + "!")]:
        with Session(engine) as db, pytest.raises(MetaAdsConnectionServiceError, match="state"):
            MetaAdsConnectionService(db, settings=settings, token_exchange_client=Exchange()).complete_callback(attempt_w, attempt_u, state=value, code="x")
    with Session(engine) as db:
        w2 = Workspace(name="Other", slug=uuid4().hex); db.add(w2); db.commit(); other = w2.id
    with Session(engine) as db, pytest.raises(MetaAdsConnectionServiceError, match="state"):
        MetaAdsConnectionService(db, settings=settings, token_exchange_client=Exchange()).complete_callback(other, uid, state=state, code="x")
    exchange = Exchange()
    def finish():
        with Session(engine) as db:
            try:
                MetaAdsConnectionService(db, settings=settings, token_exchange_client=exchange).complete_callback(wid, uid, state=state, code="x")
                return "success"
            except MetaAdsConnectionServiceError as exc:
                return exc.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: finish(), range(2)))
    assert sorted(results) == ["invalid_state", "success"]
    assert exchange.calls == 1
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(MetaAdsOAuthState).where(MetaAdsOAuthState.workspace_id == wid)) == 0
        c = db.scalar(select(MetaAdConnection).where(MetaAdConnection.workspace_id == wid))
        assert TOKEN not in c.encrypted_access_token
        assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.workspace_id == wid)) == 2


def test_expired_and_mock_state_never_exchange(fixture):
    from app.integrations.meta_ads.oauth_state import generate_mock_oauth_state
    wid, uid, settings = fixture
    with Session(engine) as db:
        start = MetaAdsConnectionService(db, settings=settings).start_oauth(wid, uid)
        db.execute(update(MetaAdsOAuthState).where(MetaAdsOAuthState.workspace_id == wid).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
        db.commit()
    state = parse_qs(urlparse(start.authorization_url).query)["state"][0]
    exchange = Exchange()
    for value in [state, generate_mock_oauth_state(wid, uid)[0]]:
        with Session(engine) as db, pytest.raises(MetaAdsConnectionServiceError):
            MetaAdsConnectionService(db, settings=settings, token_exchange_client=exchange).complete_callback(wid, uid, state=value, code="x")
    assert exchange.calls == 0


def test_explicit_account_grant_currency_selection_and_isolation(fixture):
    connect(fixture)
    with pytest.raises(MetaAdsConnectionServiceError) as exc:
        sync(fixture)
    assert exc.value.code == "account_selection_required"
    with pytest.raises(MetaAdsConnectionServiceError) as exc:
        select_account(fixture, "act_999")
    assert exc.value.code == "account_not_granted"
    with pytest.raises(MetaAdsConnectionServiceError) as exc:
        select_account(fixture, "act_456")
    assert exc.value.code == "currency_mismatch"
    assert select_account(fixture).can_sync
    wid, uid, settings = fixture
    with Session(engine) as db:
        w = Workspace(name="Other", slug=uuid4().hex); db.add(w); db.commit()
        with pytest.raises(MetaAdsConnectionServiceError):
            MetaAdsLiveSyncService(db, settings=settings, reader_factory=Reader).accounts(w.id, uid)


def test_concurrent_idempotent_sync_and_preserved_crm_attribution(fixture):
    connect(fixture); select_account(fixture)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: sync(fixture), range(2)))
    assert sum(r["metrics_created"] for r in results) == 1
    wid = fixture[0]
    with Session(engine) as db:
        metrics = db.scalars(select(AdMetric).where(AdMetric.workspace_id == wid)).all()
        assert len(metrics) == 1
        metric = metrics[0]
        metric.orders, metric.revenue, metric.net_profit, metric.leads = 4, 250, 100, 7
        db.commit()
    sync(fixture)
    with Session(engine) as db:
        metric = db.scalar(select(AdMetric).where(AdMetric.workspace_id == wid))
        assert (metric.orders, metric.revenue, metric.net_profit, metric.leads) == (4, 250, 100, 7)
        assert str(metric.spend) == "12.30" and metric.reach == 0


@pytest.mark.parametrize("conflict", ["name", "metric"])
def test_manual_csv_conflicts_roll_back_all_imports(fixture, conflict):
    connect(fixture); select_account(fixture)
    if conflict == "metric":
        sync(fixture)
    with Session(engine) as db:
        if conflict == "name":
            db.add(AdCampaign(workspace_id=fixture[0], name="  SYNTHETIC   campaign ", platform="INSTAGRAM"))
        else:
            metric = db.scalar(select(AdMetric).where(AdMetric.workspace_id == fixture[0]))
            metric.source_type, metric.spend = "CSV", 999
        db.commit()
    with pytest.raises(MetaAdsConnectionServiceError) as exc:
        sync(fixture)
    assert exc.value.code == "manual_spend_conflict"
    with Session(engine) as db:
        rows = db.scalars(select(AdMetric).where(AdMetric.workspace_id == fixture[0])).all()
        assert not rows if conflict == "name" else rows[0].spend == 999
        c = db.scalar(select(MetaAdConnection).where(MetaAdConnection.workspace_id == fixture[0]))
        assert c.last_error_code == "manual_spend_conflict"


@pytest.mark.parametrize("mutation", ["disconnect", "account"])
def test_inflight_fetch_cannot_import_after_connection_change(fixture, mutation):
    connect(fixture); select_account(fixture)
    wid, uid, settings = fixture
    class RacingReader(Reader):
        def get_campaign_insights_preview(self, account, start, end):
            with Session(engine) as other:
                if mutation == "disconnect":
                    MetaAdsConnectionService(other, settings=settings).disconnect(wid, uid)
                else:
                    MetaAdsLiveSyncService(other, settings=settings, reader_factory=Reader).select_account(wid, uid, "act_789")
            return super().get_campaign_insights_preview(account, start, end)
    with pytest.raises(MetaAdsConnectionServiceError) as exc:
        sync(fixture, RacingReader)
    assert exc.value.code == "connection_changed"
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(AdMetric).where(AdMetric.workspace_id == wid)) == 0


@pytest.mark.parametrize("role", ["OWNER", "MANAGER", "ANALYST"])
def test_actual_routes_enforce_owner_and_scoped_service(fixture, monkeypatch, role):
    wid, uid, settings = fixture
    import app.services.meta_ads_connection_service as module
    monkeypatch.setattr(module, "get_settings", lambda: settings)
    app = FastAPI(); app.include_router(router, prefix="/api/v1")
    user = SimpleNamespace(id=uid, workspaces=[SimpleNamespace(workspace_id=wid,
        workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name=role))])
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_workspace_id] = lambda: wid
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    client = TestClient(app)
    response = client.post("/api/v1/integrations/meta-ads/oauth/start")
    assert response.status_code == (200 if role == "OWNER" else 403)
    for method, path, payload in [("GET", "/accounts", None), ("POST", "/account", {"external_account_id": "act_123"}),
                                 ("POST", "/sync", {"date_from": str(DAY), "date_to": str(DAY)})]:
        result = client.request(method, "/api/v1/integrations/meta-ads" + path, json=payload)
        assert result.status_code == (409 if role == "OWNER" else 403)


def test_reconnect_invalidates_older_state_and_disconnect_is_ads_local(fixture):
    wid, uid, settings = fixture
    with Session(engine) as db:
        service = MetaAdsConnectionService(db, settings=settings, token_exchange_client=Exchange())
        a = service.start_oauth(wid, uid)
        service.start_oauth(wid, uid)
        with pytest.raises(MetaAdsConnectionServiceError):
            service.complete_callback(wid, uid, state=parse_qs(urlparse(a.authorization_url).query)["state"][0], code="x")
        result = service.disconnect(wid, uid)
        assert result.connection_status == "DISCONNECTED"
        c = db.scalar(select(MetaAdConnection).where(MetaAdConnection.workspace_id == wid))
        assert c.encrypted_access_token is None
        assert db.scalar(select(func.count()).select_from(MetaAdsOAuthState).where(MetaAdsOAuthState.workspace_id == wid)) == 0


def test_owner_http_flow_and_public_redirect_only(fixture, monkeypatch):
    wid, uid, settings = fixture
    import app.api.v1.meta_ads as api
    import app.services.meta_ads_connection_service as module
    monkeypatch.setattr(module, "get_settings", lambda: settings)
    monkeypatch.setattr(module, "MetaLiveOAuthClient", lambda **_: Exchange())
    monkeypatch.setattr(api, "MetaAdsLiveSyncService", lambda db: MetaAdsLiveSyncService(
        db, settings=settings, reader_factory=Reader))
    app = FastAPI(); app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uid, workspaces=[
        SimpleNamespace(workspace_id=wid, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name="OWNER"))])
    app.dependency_overrides[get_workspace_id] = lambda: wid
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    client = TestClient(app)
    prefix = "/api/v1/integrations/meta-ads"
    start = client.post(prefix + "/oauth/start")
    assert start.status_code == 200
    state = parse_qs(urlparse(start.json()["authorization_url"]).query)["state"][0]
    redirect = client.get(prefix + "/oauth/callback", params={"code": "synthetic-code", "state": state},
        follow_redirects=False)
    assert redirect.status_code == 303 and redirect.headers["Cache-Control"] == "no-store"
    assert redirect.headers["Location"].startswith(settings.meta_ads_oauth_frontend_callback_url)
    callback = client.post(prefix + "/oauth/callback", json={"code": "synthetic-code", "state": state})
    assert callback.status_code == 200 and callback.json()["account_selection_required"]
    accounts = client.get(prefix + "/accounts")
    assert accounts.status_code == 200 and len(accounts.json()["accounts"]) == 3
    assert accounts.json()["selected_account_id"] is None
    assert client.post(prefix + "/account", json={"external_account_id": "act_123"}).status_code == 200
    synced = client.post(prefix + "/sync", json={"date_from": str(DAY), "date_to": str(DAY)})
    assert synced.status_code == 200 and synced.json()["metrics_created"] == 1
    assert TOKEN not in synced.text + callback.text + accounts.text
    assert client.post(prefix + "/disconnect").status_code == 200
    assert client.get(prefix + "/accounts").status_code == 409


def test_provider_expiry_and_rate_limit_are_durable_and_retryable(fixture):
    from app.integrations.meta_ads.live_read_only_client import MetaReadOnlyClientError, MetaReadOnlyErrorCode
    connect(fixture); select_account(fixture)
    class LimitedReader(Reader):
        def list_ad_accounts(self):
            raise MetaReadOnlyClientError(MetaReadOnlyErrorCode.RATE_LIMITED)
    with pytest.raises(MetaAdsConnectionServiceError) as exc:
        sync(fixture, LimitedReader)
    assert exc.value.code == "RATE_LIMITED"
    with Session(engine) as db:
        c = db.scalar(select(MetaAdConnection).where(MetaAdConnection.workspace_id == fixture[0]))
        assert c.last_error_code == "RATE_LIMITED" and c.last_synced_at is None and c.last_sync_attempt_at is not None
    assert sync(fixture)["status"] == "SUCCEEDED"
    class ExpiredReader(Reader):
        def list_ad_accounts(self):
            raise MetaReadOnlyClientError(MetaReadOnlyErrorCode.TOKEN_EXPIRED)
    with pytest.raises(MetaAdsConnectionServiceError):
        sync(fixture, ExpiredReader)
    with Session(engine) as db:
        c = db.scalar(select(MetaAdConnection).where(MetaAdConnection.workspace_id == fixture[0]))
        assert c.connection_status == "TOKEN_EXPIRED" and c.last_synced_at is not None


@pytest.mark.parametrize("field,value", [
    ("spend", "999.00"), ("impressions", 999), ("clicks", 99),
    ("messages", 99), ("metric_date", "2026-10-02"),
])
def test_live_metric_http_edit_then_sync_protects_delivery_and_allows_crm(fixture, field, value):
    from app.api.v1.advertising import router as advertising_router
    connect(fixture); select_account(fixture); sync(fixture)
    wid, uid, _ = fixture
    with Session(engine) as db:
        metric_id = db.scalar(select(AdMetric.id).where(AdMetric.workspace_id == wid))
    app = FastAPI(); app.include_router(advertising_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uid, workspaces=[
        SimpleNamespace(workspace_id=wid, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name="OWNER"))])
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    client = TestClient(app, headers={"X-Workspace-ID": str(wid)})
    path = f"/api/v1/advertising/metrics/{metric_id}"
    rejected = client.put(path, json={field: value, "revenue": "999"})
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "provider_metric_read_only"
    assert rejected.json()["detail"]["fields"] == [field]
    sync(fixture)
    crm = client.put(path, json={"reach": 55, "leads": 3, "orders": 2, "revenue": "100.00", "net_profit": "40.00"})
    assert crm.status_code == 200
    assert crm.json()["source_type"] == "meta_live"
    assert crm.json()["provider_controlled_fields"] == ["metric_date", "spend", "impressions", "clicks", "messages"]
    # Unchanged full-form provider values are allowed, rather than blocking CRM-only edits.
    unchanged = client.put(path, json={"spend": "12.30", "metric_date": str(DAY), "orders": 4})
    assert unchanged.status_code == 200
    sync(fixture)
    with Session(engine) as db:
        metrics = db.scalars(select(AdMetric).where(AdMetric.workspace_id == wid)).all()
        assert len(metrics) == 1
        metric = metrics[0]
        assert metric.metric_date == DAY and str(metric.spend) == "12.30"
        assert (metric.impressions, metric.clicks, metric.messages) == (100, 5, 2)
        assert (metric.reach, metric.leads, metric.orders, metric.revenue, metric.net_profit) == (55, 3, 4, 100, 40)


def test_live_accounts_actual_workspace_header_membership_with_transport(fixture, monkeypatch):
    import httpx
    import app.api.v1.meta_ads as api
    from app.integrations.meta_ads.graph_transport import MetaGraphTransport
    from app.integrations.meta_ads.live_reader import MetaAdsLiveReader
    connect(fixture)
    wid, uid, settings = fixture
    calls = []
    def handler(request):
        calls.append(request)
        assert request.url.path == "/v26.0/me/adaccounts"
        return httpx.Response(200, json={"data": [{"id": "act_123", "name": "Scoped",
            "currency": "UAH", "timezone_name": "Europe/Kyiv", "account_status": 1}]})
    def reader(**kwargs):
        return MetaAdsLiveReader(**kwargs, transport=MetaGraphTransport("v26.0",
            client=httpx.Client(transport=httpx.MockTransport(handler))))
    monkeypatch.setattr(api, "MetaAdsLiveSyncService", lambda db: MetaAdsLiveSyncService(
        db, settings=settings, reader_factory=reader))
    app = FastAPI(); app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uid, workspaces=[
        SimpleNamespace(workspace_id=wid, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name="OWNER"))])
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    # get_workspace_id and the actual role/membership guards are NOT overridden.
    client = TestClient(app)
    path = "/api/v1/integrations/meta-ads/accounts"
    assert client.get(path).status_code == 400
    assert client.get(path, headers={"X-Workspace-ID": str(uuid4())}).status_code == 403
    assert not calls
    result = client.get(path, headers={"X-Workspace-ID": str(wid)})
    assert result.status_code == 200
    assert result.json()["accounts"][0]["external_account_id"] == "act_123"
    assert len(calls) == 1
    assert client.get(path, headers={"X-Workspace-ID": str(uuid4())}).status_code == 403
    assert len(calls) == 1


def test_fresh_039_revokes_inherited_private_state_privileges(fixture, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text
    import app.core.config as config_module
    from app.repositories.meta_ads_live_repository import MetaAdsLiveRepository

    # Unique disposable DB: never downgrade or alter the suite's shared schema.
    name = "meta_acl_" + uuid4().hex
    admin = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    admin.execute(text(f'CREATE DATABASE "{name}"'))
    test_engine = create_engine(engine.url.set(database=name))
    settings = fixture[2].model_copy(update={"database_url": engine.url.set(database=name).render_as_string(hide_password=False)})
    monkeypatch.setattr(config_module, "get_settings", lambda: settings)
    try:
        for role in ("anon", "authenticated"):
            admin.execute(text(f"""DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='{role}') THEN
                    CREATE ROLE "{role}" NOLOGIN;
                END IF;
            END $$"""))
        command.upgrade(Config("alembic.ini"), "202610200038")
        with test_engine.begin() as connection:
            connection.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated, PUBLIC"))
        command.upgrade(Config("alembic.ini"), "202610200039")
        with test_engine.connect() as connection:
            assert connection.scalar(text("SELECT relrowsecurity FROM pg_class WHERE oid='public.meta_ads_oauth_states'::regclass"))
            for role in ("anon", "authenticated"):
                for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
                    assert not connection.scalar(text("SELECT has_table_privilege(:role, 'public.meta_ads_oauth_states', :privilege)"),
                        {"role": role, "privilege": privilege})
            assert connection.scalar(text("SELECT count(*) FROM pg_class c, LATERAL aclexplode(c.relacl) acl "
                "WHERE c.oid='public.meta_ads_oauth_states'::regclass "
                "AND acl.grantee IN (SELECT oid FROM pg_roles WHERE rolname IN ('anon','authenticated'))")) == 0
            # Includes version-dependent privileges such as PostgreSQL17 MAINTAIN.
            # PUBLIC is pseudo-role grantee0; no accidental privilege remains.
            assert connection.scalar(text("SELECT count(*) FROM pg_class c, LATERAL aclexplode(c.relacl) acl "
                "WHERE c.oid='public.meta_ads_oauth_states'::regclass AND acl.grantee=0")) == 0
        with Session(test_engine) as db:
            workspace = Workspace(name="ACL QA", slug=uuid4().hex)
            user = User(email=uuid4().hex + "@example.invalid", password_hash="synthetic", first_name="QA", last_name="ACL")
            db.add_all([workspace, user]); db.commit()
            wid, uid = workspace.id, user.id
            repo = MetaAdsLiveRepository(db)
            repo.lock_workspace(wid)
            generation = str(uuid4())
            state, _ = repo.issue_state(wid, uid, generation)
            db.commit()
            assert repo.consume_state(wid, uid, state) == generation
            db.commit()
            assert repo.consume_state(wid, uid, state) is None
    finally:
        test_engine.dispose()
        admin.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.close()


def _bounded_session():
    """Bound every transaction, including the service's post-network transaction."""
    from sqlalchemy import event
    db = Session(engine)
    @event.listens_for(db, "after_begin")
    def timeouts(session, transaction, connection):
        connection.exec_driver_sql("SET LOCAL statement_timeout = '8s'")
        connection.exec_driver_sql("SET LOCAL lock_timeout = '6s'")
    return db


def _wait_until_blocked(waiter, blocker):
    """Observe the actual server wait; an event before execute alone is not proof."""
    from time import monotonic
    from threading import Event
    from sqlalchemy import text
    deadline = monotonic() + 5
    with _bounded_session() as observer:
        while monotonic() < deadline:
            if blocker in observer.scalar(text("SELECT pg_blocking_pids(:pid)"), {"pid": waiter}):
                return
            Event().wait(0.01)
    raise AssertionError("Expected PostgreSQL lock wait was not observed")


@pytest.mark.parametrize("mutation", ["update", "delete"])
def test_actual_crm_mutation_during_sync_has_no_fk_deadlock(fixture, mutation):
    from threading import Event
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    from app.schemas.advertising import AdMetricUpdate
    from app.services.advertising_service import AdMetricService

    connect(fixture); select_account(fixture); sync(fixture)
    wid, uid, settings = fixture
    with Session(engine) as db:
        metric_id = db.scalar(select(AdMetric.id).where(AdMetric.workspace_id == wid))
    metric_locked, sync_at_metrics, release_editor = Event(), Event(), Event()
    pids = {}

    class UpdatedReader(Reader):
        def get_campaign_insights_preview(self, account, start, end):
            return [MetaInsightsRowDTO("12345", DAY, "19.75", 200, 9, 4, currency="UAH")]

    def edit():
        with _bounded_session() as db:
            service = AdMetricService(db)
            get = service.metrics.get
            def locked_get(*args):
                metric = get(*args)  # Actual FOR UPDATE, no mocked persistence.
                pids["editor"] = db.scalar(text("SELECT pg_backend_pid()"))
                metric_locked.set()
                assert release_editor.wait(5), "Editor barrier timed out"
                return metric
            service.metrics.get = locked_get
            try:
                if mutation == "update":
                    service.update(wid, metric_id, AdMetricUpdate(
                        reach=55, leads=3, orders=4, revenue="100", net_profit="40"), uid)
                else:
                    service.delete(wid, metric_id, uid)
                return "committed"
            except DBAPIError as exc:
                return "database_error:" + str(exc.orig.sqlstate)

    def import_metrics():
        with _bounded_session() as db:
            service = MetaAdsLiveSyncService(db, settings=settings, reader_factory=UpdatedReader)
            metrics = service.repository.metrics
            def waiting_metrics(*args):
                pids["sync"] = db.scalar(text("SELECT pg_backend_pid()"))
                sync_at_metrics.set()
                return metrics(*args)  # Actual sync persistence and fresh locked rows.
            service.repository.metrics = waiting_metrics
            try:
                return service.sync(wid, uid, DAY, DAY)["status"]
            except MetaAdsConnectionServiceError as exc:
                return exc.code
            except DBAPIError as exc:
                return "database_error:" + str(exc.orig.sqlstate)

    with ThreadPoolExecutor(max_workers=2) as pool:
        editing = pool.submit(edit)
        try:
            assert metric_locked.wait(5), "Metric lock was not acquired"
            importing = pool.submit(import_metrics)
            assert sync_at_metrics.wait(5), "Sync did not reach persistence"
            _wait_until_blocked(pids["sync"], pids["editor"])
        finally:
            release_editor.set()
        results = editing.result(timeout=12), importing.result(timeout=12)
    assert results == ("committed", "SUCCEEDED" if mutation == "update" else "manual_spend_conflict")

    with Session(engine) as db:
        campaigns = db.scalars(select(AdCampaign).where(AdCampaign.workspace_id == wid)).all()
        metrics = db.scalars(select(AdMetric).where(AdMetric.workspace_id == wid)).all()
        assert len(campaigns) == len(metrics) == 1
        campaign, metric = campaigns[0], metrics[0]
        assert (campaign.external_source, campaign.external_account_id,
                campaign.external_campaign_id, campaign.sync_source) == ("meta_ads", "act_123", "12345", "meta_live")
        assert metric.id == metric_id and metric.campaign_id == campaign.id and metric.metric_date == DAY
        assert (metric.external_source, metric.external_account_id,
                metric.external_campaign_id, metric.source_type) == ("meta_ads", "act_123", "12345", "meta_live")
        action = "AD_METRIC_UPDATE" if mutation == "update" else "AD_METRIC_DELETE"
        assert db.scalar(select(func.count()).select_from(AuditLog).where(
            AuditLog.workspace_id == wid, AuditLog.entity_id == str(metric_id), AuditLog.action == action)) == 1
        connection = db.scalar(select(MetaAdConnection).where(MetaAdConnection.workspace_id == wid))
        if mutation == "update":
            assert metric.deleted_at is None and connection.last_error_code is None
            assert (str(metric.spend), metric.impressions, metric.clicks, metric.messages) == ("19.75", 200, 9, 4)
            assert (metric.reach, metric.leads, metric.orders, metric.revenue, metric.net_profit) == (55, 3, 4, 100, 40)
        else:
            assert metric.deleted_at is not None and metric.deleted_by == uid
            assert connection.last_error_code == "manual_spend_conflict"
            assert (str(metric.spend), metric.impressions, metric.clicks, metric.messages) == ("12.30", 100, 5, 2)


def test_workspace_mutex_emits_no_key_update_and_remains_exclusive(fixture):
    from threading import Event
    from sqlalchemy import event, text
    from app.repositories.meta_ads_live_repository import MetaAdsLiveRepository

    wid = fixture[0]
    attempting = Event()
    pids, statements = {}, []
    with _bounded_session() as first:
        connection = first.connection()
        @event.listens_for(connection, "before_cursor_execute")
        def capture(conn, cursor, statement, parameters, context, executemany):
            if "FROM workspaces" in statement:
                statements.append(statement)  # Never capture bind values.
        first_pid = first.scalar(text("SELECT pg_backend_pid()"))
        MetaAdsLiveRepository(first).lock_workspace(wid)

        def contender():
            with _bounded_session() as second:
                pids["second"] = second.scalar(text("SELECT pg_backend_pid()"))
                attempting.set()
                MetaAdsLiveRepository(second).lock_workspace(wid)
                return "acquired"

        with ThreadPoolExecutor(max_workers=1) as pool:
            waiting = pool.submit(contender)
            try:
                assert attempting.wait(5), "Second lock attempt did not start"
                _wait_until_blocked(pids["second"], first_pid)
            finally:
                first.rollback()
            assert waiting.result(timeout=12) == "acquired"
    assert len(statements) == 1
    assert statements[0].rstrip().endswith("FOR NO KEY UPDATE")


@pytest.mark.parametrize("kind", ["campaign", "metric"])
@pytest.mark.parametrize("writer", ["manual", "csv"])
def test_new_manual_csv_insert_under_workspace_mutex_is_preserved(fixture, kind, writer):
    """FK checks may proceed; the ensuing sync snapshot must reject their overlap."""
    from threading import Event
    from app.schemas.advertising import AdCampaignCreate, AdMetricCreate
    from app.services.advertising_service import AdCampaignService, AdMetricService
    from app.services.import_center_service import EntityImportService
    from app.models.import_job_log import ImportJobLogStatus

    connect(fixture); select_account(fixture)
    wid, uid, settings = fixture

    class CampaignOnlyReader(Reader):
        def get_campaign_insights_preview(self, account, start, end):
            return []

    if kind == "metric":
        sync(fixture, CampaignOnlyReader)
        with Session(engine) as db:
            campaign_id = db.scalar(select(AdCampaign.id).where(AdCampaign.workspace_id == wid))
    parent_locked, release_sync = Event(), Event()

    def importing():
        with _bounded_session() as db:
            service = MetaAdsLiveSyncService(db, settings=settings, reader_factory=Reader)
            campaigns = service.repository.campaigns
            def before_snapshot(*args):
                # Actual final revalidation has acquired the workspace mutex.
                parent_locked.set()
                assert release_sync.wait(5), "Insert barrier timed out"
                return campaigns(*args)
            service.repository.campaigns = before_snapshot
            try:
                service.sync(wid, uid, DAY, DAY)
                return "unexpected_success"
            except MetaAdsConnectionServiceError as exc:
                return exc.code

    with ThreadPoolExecutor(max_workers=1) as pool:
        imported = pool.submit(importing)
        try:
            assert parent_locked.wait(5), "Sync did not acquire its parent mutex"
            with _bounded_session() as db:
                if writer == "manual":
                    if kind == "campaign":
                        AdCampaignService(db).create(wid, AdCampaignCreate(name="Synthetic campaign"), uid)
                    else:
                        AdMetricService(db).create(wid, AdMetricCreate(
                            campaign_id=campaign_id, metric_date=DAY, spend="999", reach=55, orders=4), uid)
                else:
                    raw = ({"name": "Synthetic campaign", "platform": "INSTAGRAM"} if kind == "campaign"
                           else {"campaign_id": str(campaign_id), "metric_date": str(DAY),
                                 "spend": "999", "reach": "55", "orders": "4"})
                    status, _ = EntityImportService(db).import_row(
                        wid, "ad_campaigns" if kind == "campaign" else "ad_metrics", raw,
                        {field: field for field in raw})
                    assert status == ImportJobLogStatus.SUCCESS
                    db.commit()
        finally:
            release_sync.set()
        assert imported.result(timeout=12) == "manual_spend_conflict"

    with Session(engine) as db:
        campaigns = db.scalars(select(AdCampaign).where(AdCampaign.workspace_id == wid)).all()
        metrics = db.scalars(select(AdMetric).where(AdMetric.workspace_id == wid)).all()
        assert len(campaigns) == 1
        if kind == "campaign":
            assert campaigns[0].sync_source is None
            assert not metrics
        else:
            assert len(metrics) == 1
            metric = metrics[0]
            assert metric.campaign_id == campaign_id and metric.metric_date == DAY
            assert metric.source_type is None  # Actual legacy import writer leaves ownership unset.
            assert (metric.spend, metric.reach, metric.orders) == (999, 55, 4)
            assert metric.last_synced_at is None
        connection = db.scalar(select(MetaAdConnection).where(MetaAdConnection.workspace_id == wid))
        assert connection.last_error_code == "manual_spend_conflict"
