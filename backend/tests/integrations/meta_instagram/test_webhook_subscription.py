import httpx
import pytest

from app.integrations.meta_instagram.client import MetaInstagramClient
from app.integrations.meta_instagram.config import WEBHOOK_SUBSCRIPTIONS
from app.integrations.meta_instagram.exceptions import MetaInstagramError


@pytest.mark.asyncio
async def test_subscribe_webhooks_sends_required_fields_and_bearer_token(monkeypatch):
    captured = {}

    class Response:
        headers = {"x-fb-trace-id": "trace-1"}
        def raise_for_status(self): pass
        def json(self): return {"success": True}

    class AsyncClient:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): return False
        async def post(self, url, headers=None, data=None):
            captured.update(url=url, headers=headers, data=data)
            return Response()

    import app.integrations.meta_instagram.client as module
    monkeypatch.setattr(module.httpx, "AsyncClient", AsyncClient)
    result = await MetaInstagramClient("https://graph.example", "v99.0", "secret-token").subscribe_webhooks("ig-1", WEBHOOK_SUBSCRIPTIONS)
    assert captured["url"] == "https://graph.example/v99.0/ig-1/subscribed_apps"
    assert captured["headers"] == {"Authorization": "Bearer secret-token"}
    assert captured["data"] == {
        "subscribed_fields": "messages,messaging_postbacks,messaging_seen,message_reactions"
    }
    assert result.success is True
    assert result.subscribed_fields == WEBHOOK_SUBSCRIPTIONS
    assert result.provider_request_id == "trace-1"


@pytest.mark.asyncio
async def test_get_webhook_subscription_parses_provider_confirmed_fields(monkeypatch):
    class Response:
        headers = {"x-fb-trace-id": "trace-2"}
        def raise_for_status(self): pass
        def json(self): return {"data": [{"subscribed_fields": WEBHOOK_SUBSCRIPTIONS}]}

    class AsyncClient:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): return False
        async def get(self, url, headers=None): return Response()

    import app.integrations.meta_instagram.client as module
    monkeypatch.setattr(module.httpx, "AsyncClient", AsyncClient)
    result = await MetaInstagramClient("https://graph.example", "v99.0", "secret-token").get_webhook_subscription("ig-1")
    assert result.subscribed_fields == WEBHOOK_SUBSCRIPTIONS
    assert result.provider_request_id == "trace-2"


@pytest.mark.asyncio
async def test_subscribe_webhooks_rate_limit_is_safe_error(monkeypatch):
    class Response:
        status_code = 429
        request = httpx.Request("POST", "https://graph.example/v99.0/ig-1/subscribed_apps")
        def raise_for_status(self): raise httpx.HTTPStatusError("rate", request=self.request, response=self)

    class AsyncClient:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): return False
        async def post(self, url, headers=None, data=None): return Response()

    import app.integrations.meta_instagram.client as module
    monkeypatch.setattr(module.httpx, "AsyncClient", AsyncClient)
    with pytest.raises(MetaInstagramError) as exc:
        await MetaInstagramClient("https://graph.example", "v99.0", "secret-token").subscribe_webhooks("ig-1", WEBHOOK_SUBSCRIPTIONS)
    assert exc.value.code == "META_PROVIDER_RATE_LIMITED"