import httpx
import pytest

from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.history_client import MetaInstagramHistoryClient


@pytest.mark.asyncio
async def test_history_client_uses_cursor_and_parses_conversations(monkeypatch):
    captured = {}

    class Response:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {
                "data": [{"id": "thread-1", "updated_time": "2026-07-20T10:00:00+0000"}],
                "paging": {"cursors": {"after": "cursor-2"}},
            }

    class AsyncClient:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): return False
        async def get(self, url, headers=None, params=None):
            captured.update(url=url, headers=headers, params=params)
            return Response()

    import app.integrations.meta_instagram.history_client as module
    monkeypatch.setattr(module.httpx, "AsyncClient", AsyncClient)
    page = await MetaInstagramHistoryClient("https://graph.example", "v99.0", "token").list_conversations(
        "ig-business",
        after="cursor-1",
        limit=10,
    )
    assert captured["url"] == "https://graph.example/v99.0/ig-business/conversations"
    assert captured["headers"]["Authorization"] == "Bearer token"
    assert captured["params"]["platform"] == "instagram"
    assert captured["params"]["after"] == "cursor-1"
    assert page.conversations[0].id == "thread-1"
    assert page.after_cursor == "cursor-2"


@pytest.mark.asyncio
async def test_history_client_caps_message_page_at_documented_twenty(monkeypatch):
    captured = {}

    class Response:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {
                "messages": {
                    "data": [{"id": "mid-1", "created_time": "2026-07-20T10:00:00+0000"}],
                    "paging": {"cursors": {"after": "message-cursor"}},
                }
            }

    class AsyncClient:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): return False
        async def get(self, url, headers=None, params=None):
            captured.update(url=url, params=params)
            return Response()

    import app.integrations.meta_instagram.history_client as module
    monkeypatch.setattr(module.httpx, "AsyncClient", AsyncClient)
    page = await MetaInstagramHistoryClient("https://graph.example", "v99.0", "token").list_messages(
        "thread-1",
        limit=200,
    )
    assert "messages.limit(20)" in captured["params"]["fields"]
    assert page.messages[0].id == "mid-1"
    assert page.after_cursor == "message-cursor"


@pytest.mark.asyncio
async def test_history_client_maps_rate_limit_to_safe_error(monkeypatch):
    class Response:
        status_code = 429
        request = httpx.Request("GET", "https://graph.example/v99.0/ig-business/conversations")
        def raise_for_status(self):
            raise httpx.HTTPStatusError("rate", request=self.request, response=self)

    class AsyncClient:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): return False
        async def get(self, url, headers=None, params=None): return Response()

    import app.integrations.meta_instagram.history_client as module
    monkeypatch.setattr(module.httpx, "AsyncClient", AsyncClient)
    with pytest.raises(MetaInstagramError) as exc:
        await MetaInstagramHistoryClient("https://graph.example", "v99.0", "token").list_conversations("ig-business")
    assert exc.value.code == "META_HISTORY_RATE_LIMITED"
