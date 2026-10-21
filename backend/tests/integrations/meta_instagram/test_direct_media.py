from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.integrations.meta_instagram.media import (
    MEDIA_LABELS, normalize_attachments, public_attachments, private_media_path, valid_source_url,
)
from app.integrations.meta_instagram.services.inbound_message_service import InstagramInboundMessageService


def test_webhook_photo_post_payment_screenshot_and_text_are_preserved():
    source = "https://lookaside.fbsbx.com/example/private?token=private"
    message = {
        "text": "Ось оплата",
        "attachments": [
            {"type": "image", "payload": {"url": source}},
            {"type": "ig_post", "payload": {"url": source}},
            {"type": "image", "payload": {"url": source}},
        ],
    }
    service = InstagramInboundMessageService.__new__(InstagramInboundMessageService)
    metadata = service._metadata(message, {})
    assert len(metadata["attachments"]) == 3
    assert service._payload(message, {})[0] == "TEXT"
    public = public_attachments(metadata)
    assert len(public) == 3
    assert public[0]["label"] == "Фото"
    assert public[1]["label"] == MEDIA_LABELS["ig_post"]
    assert all("source_url" not in record for record in public)
    assert source not in str(public)


def test_invalid_media_hosts_ports_protocols_and_credentials_rejected():
    for url in [
        "http://lookaside.fbsbx.com/image",
        "https://lookaside.fbsbx.com.evil.example/image",
        "https://127.0.0.1/image",
        "https://user:pass@lookaside.fbsbx.com/image",
        "https://lookaside.fbsbx.com:8443/image",
        "https://lookaside.fbsbx.com:bad/image",
        "file:///etc/passwd",
    ]:
        assert not valid_source_url(url), url
    assert valid_source_url("https://lookaside.fbsbx.com/image")
    assert normalize_attachments({
        "attachments": [{"type": "image", "payload": {"url": "http://localhost/x"}}]
    }) == [{"type": "image"}]


def test_workspace_scoped_media_cache_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("DIRECT_MEDIA_STORAGE_PATH", str(tmp_path))
    ws_a, ws_b, msg = uuid4(), uuid4(), uuid4()
    assert private_media_path(ws_a, msg, 0) != private_media_path(ws_b, msg, 0)
    assert str(private_media_path(ws_a, msg, 0)).startswith(str(tmp_path))
    assert public_attachments(None) == []
    assert public_attachments({"attachments": [{"type": "video", "cached": True}]})[0]["available"]


@pytest.mark.asyncio
async def test_history_cursor_requests_next_messages_edge(monkeypatch):
    from app.integrations.meta_instagram.history_client import MetaInstagramHistoryClient
    import app.integrations.meta_instagram.history_client as module
    captured = {}

    class FakeClient:
        def __init__(self, timeout):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def get(self, url, headers=None, params=None):
            captured.update(url=url, params=params)
            return SimpleNamespace(
                status_code=200, raise_for_status=lambda: None,
                json=lambda: {"data": [{"id": "mid-older"}], "paging": {"cursors": {"after": "next"}}},
            )

    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)
    page = await MetaInstagramHistoryClient("https://graph.example", "v99.0", "token").list_messages(
        "thread-1", after="cursor-1", limit=20
    )
    assert captured["url"].endswith("/thread-1/messages")
    assert captured["params"]["after"] == "cursor-1"
    assert page.messages[0].id == "mid-older"
    assert page.after_cursor == "next"


def test_media_response_never_contains_provider_urls():
    from app.schemas.ai_direct import DirectMessageResponse
    assert "attachment_metadata" not in DirectMessageResponse.model_fields
    assert "attachments" in DirectMessageResponse.model_fields
