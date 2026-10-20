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


class LiveMetaAdsReadOnlyClient:
    """Compatibility facade for the validated official-host live reader."""
    def __new__(cls, *, access_token, api_version, http_client=None,
                base_url="https://graph.facebook.com", timeout_seconds=10.0):
        from app.integrations.meta_ads.graph_transport import MetaGraphTransport
        from app.integrations.meta_ads.live_reader import MetaAdsLiveReader
        if base_url != "https://graph.facebook.com":
            raise MetaReadOnlyClientError(MetaReadOnlyErrorCode.CONFIG_MISSING)
        return MetaAdsLiveReader(access_token=access_token, api_version=api_version,
            transport=MetaGraphTransport(api_version, client=http_client))
