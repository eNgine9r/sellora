from __future__ import annotations

from datetime import date

import httpx
import pytest

from app.integrations.meta_ads.live_read_only_client import LiveMetaAdsReadOnlyClient, MetaReadOnlyClientError, MetaReadOnlyErrorCode


class FakeResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeHttpClient:
    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls = []

    def get(self, url, *, params, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        if self.error:
            raise self.error
        return self.response


def _client(response=None, error=None):
    return LiveMetaAdsReadOnlyClient(
        access_token="synthetic-token-for-tests-only",
        api_version="v20.0",
        http_client=FakeHttpClient(response=response, error=error),
    )


def test_live_read_only_client_has_no_write_methods() -> None:
    client = _client(FakeResponse(200, {"data": []}))

    assert hasattr(client, "list_ad_accounts")
    assert hasattr(client, "list_campaigns")
    assert hasattr(client, "get_campaign_insights_preview")
    assert not hasattr(client, "create_campaign")
    assert not hasattr(client, "update_campaign")
    assert not hasattr(client, "delete_campaign")
    assert not hasattr(client, "upload_customer_event")


@pytest.mark.parametrize(
    ("status_code", "payload", "expected"),
    [
        (403, {"error": {"message": "Permissions error", "code": 200}}, MetaReadOnlyErrorCode.PERMISSION_MISSING),
        (400, {"error": {"message": "Token expired", "code": 190, "error_subcode": 463}}, MetaReadOnlyErrorCode.TOKEN_EXPIRED),
        (401, {"error": {"message": "Invalid OAuth token", "code": 190}}, MetaReadOnlyErrorCode.TOKEN_INVALID),
        (429, {"error": {"message": "Rate limit"}}, MetaReadOnlyErrorCode.RATE_LIMITED),
    ],
)
def test_live_client_maps_meta_errors_safely(status_code, payload, expected) -> None:
    client = _client(FakeResponse(status_code, payload))

    with pytest.raises(MetaReadOnlyClientError) as exc_info:
        client.list_ad_accounts()

    assert exc_info.value.code == expected
    assert "synthetic-token-for-tests-only" not in str(exc_info.value)
    assert "access_token" not in str(exc_info.value)


def test_live_client_maps_network_timeout_safely() -> None:
    client = _client(error=httpx.TimeoutException("timeout while connecting"))

    with pytest.raises(MetaReadOnlyClientError) as exc_info:
        client.list_ad_accounts()

    assert exc_info.value.code == MetaReadOnlyErrorCode.NETWORK_ERROR
    assert "synthetic-token-for-tests-only" not in str(exc_info.value)


def test_live_client_maps_malformed_response_safely() -> None:
    client = _client(FakeResponse(200, {"unexpected": []}))

    with pytest.raises(MetaReadOnlyClientError) as exc_info:
        client.list_ad_accounts()

    assert exc_info.value.code == MetaReadOnlyErrorCode.MALFORMED_RESPONSE


def test_live_client_maps_successful_preview_dtos_without_returning_token() -> None:
    http_client = FakeHttpClient(
        response=FakeResponse(
            200,
            {
                "data": [
                    {"id": "fake_live_act_001", "name": "Synthetic account", "currency": "UAH", "timezone_name": "Europe/Kyiv"}
                ]
            },
        )
    )
    client = LiveMetaAdsReadOnlyClient(access_token="synthetic-token-for-tests-only", api_version="v20.0", http_client=http_client)

    accounts = client.list_ad_accounts()

    assert accounts[0].external_account_id == "fake_live_act_001"
    assert "synthetic-token-for-tests-only" not in str(accounts[0])
    assert http_client.calls[0]["params"]["access_token"] == "synthetic-token-for-tests-only"


def test_live_client_maps_insights_preview_without_writes() -> None:
    client = _client(
        FakeResponse(
            200,
            {"data": [{"campaign_id": "fake_campaign_001", "date_start": "2026-07-03", "spend": "12.34", "impressions": "100", "clicks": "5"}]},
        )
    )

    rows = client.get_campaign_insights_preview("fake_act_001", date(2026, 7, 3), date(2026, 7, 3))

    assert rows[0].external_campaign_id == "fake_campaign_001"
    assert not hasattr(client, "persist_ad_metrics")
