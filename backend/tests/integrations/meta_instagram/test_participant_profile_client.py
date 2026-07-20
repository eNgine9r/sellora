from types import SimpleNamespace

import httpx
import pytest

from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.profile_client import InstagramParticipantProfileClient


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.request = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url, headers, params):
        self.request = {"url": url, "headers": headers, "params": params}
        return self.response


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}
        self.request = httpx.Request("GET", "https://graph.instagram.com/v23.0/scoped")

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "provider error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )


def test_profile_client_requests_only_documented_fields(monkeypatch):
    response = FakeResponse(
        payload={
            "name": "Марія",
            "username": "maria.shop",
            "profile_pic": "https://example.test/avatar.jpg",
            "follower_count": 42,
            "is_verified_user": False,
            "is_user_follow_business": True,
            "is_business_follow_user": False,
        },
        headers={"x-fb-trace-id": "trace-1"},
    )
    fake_client = FakeClient(response)
    monkeypatch.setattr(
        "app.integrations.meta_instagram.profile_client.httpx.Client",
        lambda timeout: fake_client,
    )

    result = InstagramParticipantProfileClient(
        "https://graph.instagram.com",
        "v23.0",
        "secret-token",
    ).fetch_profile("scoped-123")

    assert fake_client.request["url"].endswith("/v23.0/scoped-123")
    assert fake_client.request["headers"] == {"Authorization": "Bearer secret-token"}
    assert "name,username,profile_pic" in fake_client.request["params"]["fields"]
    assert result.name == "Марія"
    assert result.username == "maria.shop"
    assert result.follower_count == 42
    assert result.is_user_follow_business is True
    assert result.provider_request_id == "trace-1"


def test_profile_client_maps_rate_limit_to_safe_error(monkeypatch):
    monkeypatch.setattr(
        "app.integrations.meta_instagram.profile_client.httpx.Client",
        lambda timeout: FakeClient(FakeResponse(status_code=429)),
    )

    with pytest.raises(MetaInstagramError) as exc_info:
        InstagramParticipantProfileClient(
            "https://graph.instagram.com",
            "v23.0",
            "secret-token",
        ).fetch_profile("scoped-123")

    assert exc_info.value.code == "META_PARTICIPANT_PROFILE_RATE_LIMITED"
    assert exc_info.value.status_code == 429


def test_profile_client_maps_consent_or_blocked_response_to_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.integrations.meta_instagram.profile_client.httpx.Client",
        lambda timeout: FakeClient(FakeResponse(status_code=403)),
    )

    with pytest.raises(MetaInstagramError) as exc_info:
        InstagramParticipantProfileClient(
            "https://graph.instagram.com",
            "v23.0",
            "secret-token",
        ).fetch_profile("scoped-123")

    assert exc_info.value.code == "META_PARTICIPANT_PROFILE_UNAVAILABLE"
    assert "profile" in exc_info.value.message.lower()
