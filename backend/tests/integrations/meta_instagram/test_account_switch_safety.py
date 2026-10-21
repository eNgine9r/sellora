"""Switch real Instagram Business without corrupting old test-account conversations."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.integrations.meta_instagram.client import MetaAccountProfile, MetaTokenResult, MetaWebhookSubscriptionResult
from app.integrations.meta_instagram.config import OAUTH_REQUIRED_SCOPES, WEBHOOK_SUBSCRIPTIONS
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.services.connection_service import InstagramConnectionService
from app.models.meta_instagram import InstagramConnection


class Repo:
    def __init__(self,workspace_id,old):
        self.workspace_id=workspace_id
        self.rows=[old]
        self.active=old
    def get_active(self,w):
        assert w==self.workspace_id
        return self.active
    def get_connected_in_other_workspace(self,a,w):
        return None
    def get_by_workspace_account(self,w,a):
        assert w==self.workspace_id
        return next((x for x in self.rows if x.instagram_account_id==a),None)
    def create(self,c):
        c.id=uuid4()
        self.rows.append(c)
        self.active=c
        return c


class OAuthState:
    def __init__(self,workspace_id):
        self.row=SimpleNamespace(workspace_id=workspace_id, user_id=uuid4(),redirect_uri='https://test/callback',consumed_at=None)
    def validate_state(self,*a):
        return self.row


class OAuthClient:
    def __init__(self,account):
        self.account=account
    async def exchange_code(self,**kwargs):
        return MetaTokenResult(access_token='synthetic-access-token', user_id=self.account,
                               expires_at=datetime.now(UTC)+timedelta(days=30),
                               granted_permissions=list(OAUTH_REQUIRED_SCOPES))
    async def exchange_long_lived(self,*,access_token):
        return MetaTokenResult(access_token=access_token, user_id=self.account,
                               expires_at=datetime.now(UTC)+timedelta(days=60),
                               granted_permissions=list(OAUTH_REQUIRED_SCOPES))
    async def inspect_account(self,*,access_token,token_user_id=None):
        return MetaAccountProfile(self.account,self.account,'BUSINESS',list(OAUTH_REQUIRED_SCOPES))


class WebhookClient:
    def __init__(self,*args):pass
    async def subscribe_webhooks(self,*args):
        return MetaWebhookSubscriptionResult(True,list(WEBHOOK_SUBSCRIPTIONS),'req1')
    async def get_webhook_subscription(self,*args):
        return MetaWebhookSubscriptionResult(True,list(WEBHOOK_SUBSCRIPTIONS),'req2')


def build(monkeypatch,status="CONNECTED"):
    import app.integrations.meta_instagram.services.connection_service as module
    workspace=uuid4()
    old=InstagramConnection(id=uuid4(),workspace_id=workspace,
        instagram_account_id='test-account',instagram_username='test-shop',
        instagram_account_type='BUSINESS',status=status,access_token_ciphertext='encrypted-test',
        granted_permissions=list(OAUTH_REQUIRED_SCOPES),subscribed_webhook_fields=list(WEBHOOK_SUBSCRIPTIONS))
    repo=Repo(workspace,old)
    state=OAuthState(workspace)
    monkeypatch.setattr(module,'InstagramConnectionRepository',lambda db:repo)
    monkeypatch.setattr(module,'InstagramOAuthService',lambda db:state)
    monkeypatch.setattr(module,'MetaInstagramClient',WebhookClient)
    monkeypatch.setattr(module,'encrypt_instagram_token',lambda token: ('encrypted-live','nonce','v1'))
    return repo,state,old


@pytest.mark.asyncio
async def test_active_test_account_must_be_disconnected_before_live_account_oauth(monkeypatch):
    repo,state,old=build(monkeypatch)
    svc=InstagramConnectionService(SimpleNamespace(),OAuthClient('real-store'))
    with pytest.raises(MetaInstagramError) as exc:
        await svc.complete_callback('state','synthetic-code')
    assert exc.value.code=='META_ACCOUNT_SWITCH_REQUIRES_DISCONNECT'
    assert state.row.consumed_at
    assert len(repo.rows)==1
    assert old.instagram_account_id=='test-account'
    assert old.status=='CONNECTED'
    assert old.access_token_ciphertext=='encrypted-test'


@pytest.mark.asyncio
async def test_disconnected_test_account_is_preserved_when_live_account_is_connected(monkeypatch):
    repo,state,old=build(monkeypatch,status='DISCONNECTED')
    old.access_token_ciphertext=None
    live=await InstagramConnectionService(SimpleNamespace(),OAuthClient('real-store')).complete_callback('state','code')
    assert live.status=='CONNECTED'
    assert live.id!=old.id
    assert repo.active is live
    assert live.instagram_account_id=='real-store'
    assert live.access_token_ciphertext=='encrypted-live'
    assert old.instagram_account_id=='test-account'
    assert old.status=='DISCONNECTED'
    assert old.access_token_ciphertext is None
    assert len(repo.rows)==2


@pytest.mark.asyncio
async def test_reconnect_same_account_keeps_existing_id(monkeypatch):
    repo,state,old=build(monkeypatch,status='DISCONNECTED')
    reconnected=await InstagramConnectionService(SimpleNamespace(),OAuthClient('test-account')).complete_callback('state','code')
    assert reconnected is old
    assert reconnected.instagram_account_id=='test-account'
    assert len(repo.rows)==1


@pytest.mark.asyncio
async def test_switching_back_to_old_test_account_reuses_original_record(monkeypatch):
    repo,state,old=build(monkeypatch,status='DISCONNECTED')
    live=await InstagramConnectionService(SimpleNamespace(),OAuthClient('real-store')).complete_callback('state','code')
    live.status='DISCONNECTED'
    repo.active=live
    restored=await InstagramConnectionService(SimpleNamespace(),OAuthClient('test-account')).complete_callback('state','code')
    assert restored is old
    assert len(repo.rows)==2
    assert restored.instagram_account_id=='test-account'
    assert live.instagram_account_id=='real-store'


def test_repository_active_sort_prefers_recent_reactivation():
    from app.integrations.meta_instagram.repositories.connection_repository import InstagramConnectionRepository
    from sqlalchemy.dialects import postgresql
    class DB:
        def execute(self,stmt):
            sql=str(stmt.compile(dialect=postgresql.dialect()))
            assert 'ORDER BY instagram_connections.updated_at DESC' in sql
            return SimpleNamespace(scalar_one_or_none=lambda:None)
    assert InstagramConnectionRepository(DB()).get_active(uuid4()) is None


def test_active_direct_inbox_excludes_old_test_connection_without_deleting_data():
    from app.api.v1.direct import _visible_for_connected_instagram
    current_id, old_id=uuid4(),uuid4()
    rows=[
        SimpleNamespace(channel="INSTAGRAM",instagram_connection_id=old_id),
        SimpleNamespace(channel="INSTAGRAM",instagram_connection_id=current_id),
        SimpleNamespace(channel="MANUAL",instagram_connection_id=None),
        SimpleNamespace(channel="SYNTHETIC",instagram_connection_id=None),
    ]
    current=SimpleNamespace(id=current_id,status="CONNECTED")
    selected=_visible_for_connected_instagram(rows,current)
    assert len(selected)==3
    assert rows[0] not in selected and rows[1] in selected
    assert rows[2] in selected and rows[3] in selected
    assert len(rows)==4  # historical test threads remain stored
    assert _visible_for_connected_instagram(rows,None)==rows
    assert _visible_for_connected_instagram(rows,SimpleNamespace(id=current_id,status="DISCONNECTED"))==rows
