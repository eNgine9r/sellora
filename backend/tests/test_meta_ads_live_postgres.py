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
