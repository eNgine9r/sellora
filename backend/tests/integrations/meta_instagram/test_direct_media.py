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


def test_share_post_permalink_is_preserved_without_enabling_media_download():
    from app.integrations.meta_instagram.media import normalize_instagram_post_url
    valid = "https://www.instagram.com/p/DABCdef9/?igsh=a_tracking_parameter"
    post = normalize_instagram_post_url(valid)
    assert post == "https://www.instagram.com/p/DABCdef9/"
    rows = normalize_attachments({"attachments": [
        {"type": "share", "payload": {"url": valid}}
    ]})
    assert rows == [{"type": "share", "post_url": post}]
    public = public_attachments({"attachments": rows})
    assert public[0]["available"] is True
    assert public[0]["media_available"] is False
    assert public[0]["post_url"] == post
    assert "source_url" not in str(public)
    assert normalize_attachments({"share": {"link": valid}}) == rows


def test_post_link_security_rejects_untrusted_redirects_and_invalid_slugs():
    from app.integrations.meta_instagram.media import normalize_instagram_post_url
    invalid = [
        "http://www.instagram.com/p/ABC12/",
        "https://instagram.com.evil.com/p/ABC12/",
        "https://www.instagram.com@evil.com/p/ABC12/",
        "https://www.instagram.com:8443/p/ABC12/",
        "https://www.instagram.com/p/../../ABC12",
        "https://www.instagram.com/explore/ABC12/",
        "https://www.instagram.com/p/ABC12/extra/",
        "javascript:alert(1)",
        "https://127.0.0.1/p/ABC12",
        "file:///etc/passwd",
    ]
    assert all(normalize_instagram_post_url(x) is None for x in invalid)
    assert normalize_instagram_post_url("https://www.instagram.com/reel/AB23_def/") == "https://www.instagram.com/reel/AB23_def/"
    assert not valid_source_url("https://www.instagram.com/p/ABC12/")


def test_manual_post_link_requires_blank_message_and_is_idempotent(monkeypatch):
    from types import SimpleNamespace
    from app.integrations.meta_instagram.services.share_link_service import InstagramPostLinkService, InstagramPostLinkError
    from uuid import uuid4

    ws = uuid4()
    msg = SimpleNamespace(
        id=uuid4(), workspace_id=ws, provider="INSTAGRAM",
        text="", attachment_metadata={"history_imported": True},
    )
    class FakeDB:
        def execute(self, query):
            return SimpleNamespace(scalar_one_or_none=lambda: msg)
    logs = []
    monkeypatch.setattr(
        "app.integrations.meta_instagram.services.share_link_service.AuditLogRepository",
        lambda db: SimpleNamespace(create=lambda **kw: logs.append(kw)),
    )
    service = InstagramPostLinkService(FakeDB())
    actor = uuid4()
    service.link(ws, msg.id, actor, "https://instagram.com/p/ABC1234/?utm=ignored")
    assert len(logs) == 1
    assert logs[0]["user_id"] == actor
    assert logs[0]["action"] == "DIRECT_INSTAGRAM_POST_LINKED"
    assert msg.attachment_metadata["history_imported"]
    assert msg.attachment_metadata["attachments"] == [
        {"type": "ig_post", "post_url": "https://www.instagram.com/p/ABC1234/", "source": "MANUAL"}
    ]
    service.link(ws, msg.id, actor, "https://www.instagram.com/p/ABC1234/")
    assert len(logs) == 1
    with pytest.raises(InstagramPostLinkError) as exc:
        service.link(ws, msg.id, actor, "https://www.instagram.com/p/ABCD789/")
    assert exc.value.status_code == 409


def test_manual_post_link_never_overwrites_customer_text(monkeypatch):
    from types import SimpleNamespace
    from app.integrations.meta_instagram.services.share_link_service import InstagramPostLinkService, InstagramPostLinkError
    from uuid import uuid4
    msg = SimpleNamespace(id=uuid4(), provider="INSTAGRAM", text="Маєте в наявності?", attachment_metadata=None)
    db = SimpleNamespace(execute=lambda query: SimpleNamespace(scalar_one_or_none=lambda: msg))
    with pytest.raises(InstagramPostLinkError) as exc:
        InstagramPostLinkService(db).link(uuid4(), msg.id, uuid4(), "https://www.instagram.com/p/ABC1234/")
    assert exc.value.status_code == 409
    assert msg.attachment_metadata is None
