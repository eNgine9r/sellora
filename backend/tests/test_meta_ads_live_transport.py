import json
from datetime import date
from urllib.parse import parse_qs

import httpx
import pytest

from app.integrations.meta_ads.graph_transport import MetaGraphTransport
from app.integrations.meta_ads.live_oauth_client import MetaLiveOAuthClient, MetaLiveOAuthClientError
from app.integrations.meta_ads.live_reader import MetaAdsLiveReader
from app.integrations.meta_ads.live_read_only_client import MetaReadOnlyClientError

TOKEN = "synthetic-private-provider-token"


def transport(handler):
    return MetaGraphTransport("v26.0", client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_exchange_body_only_and_permission_verification():
    calls = []
    def handler(request):
        calls.append(request)
        assert TOKEN not in str(request.url)
        assert "secret" not in str(request.url)
        if request.url.path.endswith("access_token"):
            assert request.method == "POST"
            form = parse_qs(request.content.decode())
            assert form["client_secret"] == ["synthetic-secret"]
            assert form["code"] == ["synthetic-code"]
            return httpx.Response(200, json={"access_token": TOKEN, "expires_in": 3600})
        assert request.headers["Authorization"] == "Bearer " + TOKEN
        return httpx.Response(200, json={"data": [{"permission": "ads_read", "status": "granted"}]})
    result = MetaLiveOAuthClient(app_id="123", app_secret="synthetic-secret", api_version="v26.0",
        transport=transport(handler)).exchange_code_for_token(code="synthetic-code", redirect_uri="https://example.invalid/callback")
    assert result.scopes == ("ads_read",)
    assert TOKEN not in repr(result)
    assert len(calls) == 2


@pytest.mark.parametrize("permissions", [[], [{"permission": "ads_read", "status": "declined"}], [{"permission": "ads_management", "status": "granted"}]])
def test_oauth_rejects_missing_read_permission(permissions):
    def handler(request):
        return httpx.Response(200, json={"access_token": TOKEN, "expires_in": 3600}
            if request.url.path.endswith("access_token") else {"data": permissions})
    with pytest.raises(MetaLiveOAuthClientError):
        MetaLiveOAuthClient(app_id="123", app_secret="synthetic-secret", api_version="v26.0",
            transport=transport(handler)).exchange_code_for_token(code="x", redirect_uri="https://example.invalid/callback")


def test_daily_encoding_cursor_pagination_and_no_overlapping_message_counts():
    calls = []
    def handler(request):
        calls.append(request)
        assert request.method == "GET"
        assert request.url.host == "graph.facebook.com"
        assert TOKEN not in str(request.url)
        assert request.headers["Authorization"] == "Bearer " + TOKEN
        assert request.url.params["time_increment"] == "1"
        assert json.loads(request.url.params["time_range"]) == {"since": "2026-10-01", "until": "2026-10-02"}
        day = "2026-10-02" if request.url.params.get("after") else "2026-10-01"
        response = {"data": [{"campaign_id": "1", "date_start": day, "date_stop": day,
            "spend": "12.30", "account_currency": "UAH", "actions": [
                {"action_type": "onsite_conversion.messaging_conversation_started_7d", "value": "3"},
                {"action_type": "onsite_conversion.messaging_first_reply", "value": "8"},
            ]}]}
        if len(calls) == 1:
            response["paging"] = {"next": "https://evil.invalid/?access_token=leak", "cursors": {"after": "safe_cursor"}}
        return httpx.Response(200, json=response)
    rows = MetaAdsLiveReader(access_token=TOKEN, api_version="v26.0", transport=transport(handler)).get_campaign_insights_preview(
        "act_123", date(2026, 10, 1), date(2026, 10, 2))
    assert len(rows) == 2 and all(r.messages == 3 for r in rows)
    assert len(calls) == 2


@pytest.mark.parametrize("status,payload,expected", [
    (429, {"error": {"message": TOKEN}}, "RATE_LIMITED"),
    (400, {"error": {"code": 190, "error_subcode": 463, "message": TOKEN}}, "TOKEN_EXPIRED"),
    (400, {"error": {"code": 190, "message": TOKEN}}, "TOKEN_INVALID"),
    (400, {"error": {"code": 200, "message": TOKEN}}, "PERMISSION_MISSING"),
    (200, {"error": {"code": 4, "message": TOKEN}}, "RATE_LIMITED"),
    (302, {}, "UNKNOWN_ERROR"),
])
def test_safe_errors_no_retry_storm_or_redirect(status, payload, expected):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, json=payload, headers={"Location": "https://evil.invalid/"})
    with pytest.raises(MetaReadOnlyClientError) as exc:
        transport(handler).request("/me/adaccounts", token=TOKEN)
    assert exc.value.code == expected
    assert TOKEN not in str(exc.value)
    assert len(calls) == 1  # Caller explicitly retries a manual request later.


def test_invalid_cursor_and_bounded_pages():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"data": [], "paging": {"next": "ignored", "cursors": {"after": "repeated"}}})
    reader = MetaAdsLiveReader(access_token=TOKEN, api_version="v26.0", transport=transport(handler))
    with pytest.raises(MetaReadOnlyClientError):
        reader.list_ad_accounts()
    assert len(calls) == 2


@pytest.mark.parametrize("identifier", ["../me", "act_123?token=x", "https://evil.invalid", "123"])
def test_account_path_injection_rejected(identifier):
    reader = MetaAdsLiveReader(access_token=TOKEN, api_version="v26.0",
        transport=transport(lambda _: pytest.fail("invalid account must not make request")))
    with pytest.raises(MetaReadOnlyClientError):
        reader.list_campaigns(identifier)


@pytest.mark.parametrize("version", ["v20.0", "v23.0", "../v26.0", "v999.0"])
def test_unverified_or_deprecated_marketing_versions_fail_closed(version):
    with pytest.raises(MetaReadOnlyClientError):
        MetaGraphTransport(version)
