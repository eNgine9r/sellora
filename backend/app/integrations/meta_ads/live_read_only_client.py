from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Protocol

import httpx
from pydantic import ValidationError

from app.integrations.meta_ads.schemas import MetaAdAccountDTO, MetaCampaignDTO, MetaInsightsRowDTO


class MetaReadOnlyErrorCode(StrEnum):
    PERMISSION_MISSING = "PERMISSION_MISSING"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    RATE_LIMITED = "RATE_LIMITED"
    NETWORK_ERROR = "NETWORK_ERROR"
    CONFIG_MISSING = "CONFIG_MISSING"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


SAFE_ERROR_MESSAGES: dict[MetaReadOnlyErrorCode, str] = {
    MetaReadOnlyErrorCode.PERMISSION_MISSING: "Meta Ads account access is not available. Please reconnect or check permissions.",
    MetaReadOnlyErrorCode.TOKEN_EXPIRED: "Meta Ads access has expired. Please reconnect the account.",
    MetaReadOnlyErrorCode.TOKEN_INVALID: "Meta Ads access token is invalid. Please reconnect the account.",
    MetaReadOnlyErrorCode.RATE_LIMITED: "Meta Ads temporarily limited the request. Please try again later.",
    MetaReadOnlyErrorCode.NETWORK_ERROR: "Meta Ads could not be reached safely. Please try again later.",
    MetaReadOnlyErrorCode.CONFIG_MISSING: "Meta Ads read-only client is not configured.",
    MetaReadOnlyErrorCode.MALFORMED_RESPONSE: "Meta Ads returned an unexpected read-only response.",
    MetaReadOnlyErrorCode.UNKNOWN_ERROR: "Meta Ads read-only access is not available right now.",
}


class MetaReadOnlyClientError(RuntimeError):
    """Safe live read-only client error that never includes token material."""

    def __init__(self, code: MetaReadOnlyErrorCode, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or SAFE_ERROR_MESSAGES[code])


class _HttpClient(Protocol):
    def get(self, url: str, *, params: dict[str, Any], timeout: float | None = None) -> Any: ...


class LiveMetaAdsReadOnlyClient:
    """Guarded live read-only client foundation for Meta Ads preview calls.

    This class intentionally exposes only read methods. It does not create,
    update, delete, import, schedule, or persist Meta data.
    """

    def __init__(
        self,
        *,
        access_token: str,
        api_version: str,
        base_url: str = "https://meta-graph.local",
        http_client: _HttpClient | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        if not access_token or not api_version:
            raise MetaReadOnlyClientError(MetaReadOnlyErrorCode.CONFIG_MISSING)
        self._access_token = access_token
        self._api_version = api_version.strip("/")
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client or httpx.Client()
        self._timeout_seconds = timeout_seconds

    def list_ad_accounts(self) -> list[MetaAdAccountDTO]:
        payload = self._get("/me/adaccounts", params={"fields": "id,name,currency,timezone_name,account_status"})
        data = self._extract_list(payload)
        accounts: list[MetaAdAccountDTO] = []
        for row in data:
            try:
                accounts.append(
                    MetaAdAccountDTO(
                        external_account_id=str(row.get("id") or ""),
                        name=str(row.get("name") or "Meta ad account"),
                        currency=str(row.get("currency") or "USD"),
                        timezone=str(row.get("timezone_name") or "UTC"),
                    )
                )
            except ValidationError as exc:
                raise MetaReadOnlyClientError(MetaReadOnlyErrorCode.MALFORMED_RESPONSE) from exc
        return accounts

    def list_campaigns(self, account_id: str) -> list[MetaCampaignDTO]:
        payload = self._get(f"/{account_id}/campaigns", params={"fields": "id,name,status,objective,created_time,start_time,stop_time"})
        data = self._extract_list(payload)
        campaigns: list[MetaCampaignDTO] = []
        for row in data:
            try:
                campaigns.append(
                    MetaCampaignDTO(
                        external_campaign_id=str(row.get("id") or ""),
                        external_account_id=account_id,
                        name=str(row.get("name") or "Meta campaign"),
                        status=str(row.get("status") or "UNKNOWN"),
                        objective=str(row.get("objective") or "UNKNOWN"),
                        platform="meta_ads",
                        created_time=self._parse_datetime(row.get("created_time") or row.get("start_time")),
                    )
                )
            except (TypeError, ValidationError) as exc:
                raise MetaReadOnlyClientError(MetaReadOnlyErrorCode.MALFORMED_RESPONSE) from exc
        return campaigns

    def get_campaign_insights_preview(self, account_id: str, date_from: date, date_to: date) -> list[MetaInsightsRowDTO]:
        payload = self._get(
            f"/{account_id}/insights",
            params={
                "fields": "campaign_id,date_start,spend,impressions,clicks,actions,reach",
                "time_range": {"since": date_from.isoformat(), "until": date_to.isoformat()},
                "level": "campaign",
            },
        )
        data = self._extract_list(payload)
        rows: list[MetaInsightsRowDTO] = []
        for row in data:
            try:
                rows.append(
                    MetaInsightsRowDTO(
                        external_campaign_id=str(row.get("campaign_id") or row.get("id") or ""),
                        date=date.fromisoformat(str(row.get("date_start") or date_from.isoformat())),
                        spend=Decimal(str(row.get("spend") or "0")),
                        impressions=int(row.get("impressions") or 0),
                        clicks=int(row.get("clicks") or 0),
                        messages=self._messages_from_actions(row.get("actions")),
                    )
                )
            except (ValueError, TypeError, ValidationError) as exc:
                raise MetaReadOnlyClientError(MetaReadOnlyErrorCode.MALFORMED_RESPONSE) from exc
        return rows

    def _get(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        safe_params = dict(params)
        safe_params["access_token"] = self._access_token
        try:
            response = self._http_client.get(f"{self._base_url}/{self._api_version}{path}", params=safe_params, timeout=self._timeout_seconds)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise MetaReadOnlyClientError(MetaReadOnlyErrorCode.NETWORK_ERROR) from exc
        status_code = int(getattr(response, "status_code", 0) or 0)
        try:
            payload = response.json()
        except Exception as exc:
            raise MetaReadOnlyClientError(MetaReadOnlyErrorCode.MALFORMED_RESPONSE) from exc
        if status_code >= 400:
            raise MetaReadOnlyClientError(self._map_error(status_code, payload))
        if not isinstance(payload, dict):
            raise MetaReadOnlyClientError(MetaReadOnlyErrorCode.MALFORMED_RESPONSE)
        return payload

    def _extract_list(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        data = payload.get("data")
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise MetaReadOnlyClientError(MetaReadOnlyErrorCode.MALFORMED_RESPONSE)
        return data

    def _map_error(self, status_code: int, payload: dict[str, Any]) -> MetaReadOnlyErrorCode:
        if status_code == 429:
            return MetaReadOnlyErrorCode.RATE_LIMITED
        error = payload.get("error") if isinstance(payload, dict) else None
        message = ""
        code = None
        subcode = None
        if isinstance(error, dict):
            message = str(error.get("message") or "").lower()
            code = error.get("code")
            subcode = error.get("error_subcode")
        if status_code in {401, 403} and ("permission" in message or code in {10, 200, 2500}):
            return MetaReadOnlyErrorCode.PERMISSION_MISSING
        if "expired" in message or subcode in {463, 467}:
            return MetaReadOnlyErrorCode.TOKEN_EXPIRED
        if status_code in {400, 401} and ("token" in message or "oauth" in message or code == 190):
            return MetaReadOnlyErrorCode.TOKEN_INVALID
        if status_code in {500, 502, 503, 504}:
            return MetaReadOnlyErrorCode.NETWORK_ERROR
        return MetaReadOnlyErrorCode.UNKNOWN_ERROR

    def _parse_datetime(self, value: Any) -> datetime:
        if not value:
            return datetime.now()
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    def _messages_from_actions(self, actions: Any) -> int:
        if not isinstance(actions, list):
            return 0
        total = 0
        for action in actions:
            if isinstance(action, dict) and "messaging" in str(action.get("action_type") or "").lower():
                total += int(action.get("value") or 0)
        return total
