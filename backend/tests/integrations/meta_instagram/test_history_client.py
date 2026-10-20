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
@pytest.mark.parametrize(
    ("status", "provider_code", "expected_code"),
    [
        (400, 9000001, "META_HISTORY_MESSAGE_UNAVAILABLE"),
        (404, 100, "META_HISTORY_MESSAGE_UNAVAILABLE"),
        (400, 100, "META_HISTORY_ACCESS_DENIED"),
        (403, 10, "META_HISTORY_ACCESS_DENIED"),
    ],
)
async def test_history_client_does_not_hide_permission_errors_as_missing_messages(
    monkeypatch, status, provider_code, expected_code
):
    client = MetaInstagramHistoryClient("https://graph.example", "v99.0", "token")
    request = httpx.Request("GET", "https://graph.example/v99.0/message-id")
    response = httpx.Response(
        status,
        request=request,
        json={"error": {"code": provider_code, "type": "OAuthException"}},
    )

    async def rejected_get(path, *, params):
        cause = httpx.HTTPStatusError("rejected", request=request, response=response)
        try:
            raise cause
        except httpx.HTTPStatusError as error:
            raise MetaInstagramError(
                "META_HISTORY_ACCESS_DENIED",
                "Meta rejected the history request or the item is unavailable.",
                status,
            ) from error

    monkeypatch.setattr(client, "_get", rejected_get)
    with pytest.raises(MetaInstagramError) as exc:
        await client.get_message("message-id")
    assert exc.value.code == expected_code



@pytest.mark.asyncio
async def test_history_client_reads_inline_message_details_without_individual_get(monkeypatch):
    paths = []

    class AsyncClient:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): return False
        async def get(self, url, headers=None, params=None):
            paths.append((url, params["fields"]))
            return httpx.Response(
                200, request=httpx.Request("GET", url),
                json={"messages": {"data": [{
                    "id": "mid-older", "created_time": "2026-01-01T00:00:00+0000",
                    "from": {"id": "customer"}, "to": {"data": [{"id": "business"}]},
                    "message": "Historical message",
                }]}},
            )

    import app.integrations.meta_instagram.history_client as module
    monkeypatch.setattr(module.httpx, "AsyncClient", AsyncClient)
    page = await MetaInstagramHistoryClient("https://graph.example", "v99.0", "token").list_messages("thread-1")
    assert len(paths) == 1
    assert "message,from,to" in paths[0][1]
    assert page.messages[0].details.message == "Historical message"
    assert page.messages[0].details.from_id == "customer"
    assert page.messages[0].details.to == [{"id": "business"}]


@pytest.mark.asyncio
async def test_history_client_falls_back_when_inline_fields_unsupported(monkeypatch):
    calls = []

    class AsyncClient:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): return False
        async def get(self, url, headers=None, params=None):
            calls.append(params["fields"])
            request = httpx.Request("GET", url)
            if len(calls) == 1:
                response = httpx.Response(400, request=request, json={
                    "error": {"code": 100, "message": "Tried accessing nonexisting field (message)"}
                })
            else:
                response = httpx.Response(200, request=request, json={
                    "messages": {"data": [{"id": "mid-basic"}]}
                })
            response.raise_for_status()
            return response

    import app.integrations.meta_instagram.history_client as module
    monkeypatch.setattr(module.httpx, "AsyncClient", AsyncClient)
    page = await MetaInstagramHistoryClient("https://graph.example", "v99.0", "token").list_messages("thread-1")
    assert len(calls) == 2
    assert page.messages[0].id == "mid-basic"
    assert page.messages[0].details is None


@pytest.mark.asyncio
async def test_history_client_retries_details_with_minimal_supported_fields(monkeypatch):
    calls = []

    class AsyncClient:
        def __init__(self, timeout): pass
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): return False
        async def get(self, url, headers=None, params=None):
            calls.append(params["fields"])
            request = httpx.Request("GET", url)
            if len(calls) == 1:
                response = httpx.Response(400, request=request, json={
                    "error": {"code": 100, "message": "Tried accessing nonexisting field (reply_to)"}
                })
            else:
                response = httpx.Response(200, request=request, json={
                    "id": "mid-1", "from": {"id": "customer"}, "to": {"data": [{"id": "business"}]},
                    "message": "Past purchase",
                })
            response.raise_for_status()
            return response

    import app.integrations.meta_instagram.history_client as module
    monkeypatch.setattr(module.httpx, "AsyncClient", AsyncClient)
    details = await MetaInstagramHistoryClient("https://graph.example", "v99.0", "token").get_message("mid-1")
    assert len(calls) == 2
    assert details.message == "Past purchase"
