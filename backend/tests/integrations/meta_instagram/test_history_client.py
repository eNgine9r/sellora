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


@pytest.mark.asyncio
async def test_history_client_keeps_inline_photo_from_nested_messages(monkeypatch):
    client = MetaInstagramHistoryClient("https://graph.example", "v99.0", "token")
    captured = []

    async def fake_get(path, *, params):
        captured.append(params["fields"])
        return {
            "messages": {"data": [{
                "id": "mid-image", "created_time": "2026-10-21T12:00:00+0000",
                "from": {"id": "customer-1"}, "to": {"data": [{"id": "business-1"}]},
                "attachments": {"data": [{"image_data": {"url": "https://lookaside.fbsbx.com/photo.jpg"}}]},
            }]}
        }

    monkeypatch.setattr(client, "_get", fake_get)
    page = await client.list_messages("thread-image")
    assert "attachments" in captured[0]
    assert len(page.messages) == 1
    assert page.messages[0].details is not None
    assert page.messages[0].details.attachments == [
        {"type": "image", "source_url": "https://lookaside.fbsbx.com/photo.jpg"}
    ]


@pytest.mark.asyncio
async def test_history_client_optional_field_fallback_preserves_media(monkeypatch):
    client = MetaInstagramHistoryClient("https://graph.example", "v99.0", "token")
    requested = []

    async def fake_get(path, *, params):
        requested.append(params["fields"])
        if "reply_to" in params["fields"]:
            raise MetaInstagramError("META_HISTORY_ACCESS_DENIED", "unsupported optional field", 400)
        return {
            "id": "mid-photo",
            "from": {"id": "customer-1"},
            "to": {"data": [{"id": "business-1"}]},
            "attachments": {"data": [{"image_data": {"url": "https://lookaside.fbsbx.com/photo.jpg"}}]},
        }

    monkeypatch.setattr(client, "_get", fake_get)
    monkeypatch.setattr(client, "_unsupported_fields_error", lambda exc: exc.status_code == 400)
    message = await client.get_message("mid-photo")
    assert len(requested) == 2
    assert "attachments" in requested[1]
    assert "reply_to" not in requested[1]
    assert message.attachments[0]["source_url"] == "https://lookaside.fbsbx.com/photo.jpg"


@pytest.mark.asyncio
async def test_history_client_does_not_discard_rate_limit_during_media_fallback(monkeypatch):
    client = MetaInstagramHistoryClient("https://graph.example", "v99.0", "token")
    calls = []

    async def fake_get(path, *, params):
        calls.append(params["fields"])
        raise MetaInstagramError("META_HISTORY_RATE_LIMITED", "rate limited", 429)

    monkeypatch.setattr(client, "_get", fake_get)
    with pytest.raises(MetaInstagramError) as exc:
        await client.get_message("mid-photo")
    assert exc.value.code == "META_HISTORY_RATE_LIMITED"
    assert len(calls) == 1
