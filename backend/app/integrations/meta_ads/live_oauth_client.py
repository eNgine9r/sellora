from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import urlencode

from app.integrations.meta_ads.graph_transport import MetaGraphTransport
from app.integrations.meta_ads.live_read_only_client import MetaReadOnlyClientError


class MetaLiveOAuthClientError(RuntimeError):
    """Safe OAuth failure without provider response or credentials."""


@dataclass(frozen=True)
class MetaTokenExchangeResult:
    access_token: str = field(repr=False)
    expires_at: datetime | None = None
    scopes: tuple[str, ...] = ()


class MetaLiveOAuthClientProtocol(Protocol):
    def exchange_code_for_token(self, *, code: str, redirect_uri: str) -> MetaTokenExchangeResult: ...


class DisabledMetaLiveOAuthClient:
    def exchange_code_for_token(self, *, code: str, redirect_uri: str) -> MetaTokenExchangeResult:
        raise MetaLiveOAuthClientError("Live Meta OAuth is disabled.")


class MetaLiveOAuthClient:
    def __init__(self, *, app_id: str, app_secret: str, api_version: str, transport=None):
        self.app_id = app_id
        self.app_secret = app_secret
        self.transport = transport or MetaGraphTransport(api_version)

    def exchange_code_for_token(self, *, code: str, redirect_uri: str) -> MetaTokenExchangeResult:
        try:
            payload = self.transport.request("/oauth/access_token", form={
                "client_id": self.app_id, "client_secret": self.app_secret,
                "redirect_uri": redirect_uri, "code": code,
            })
            token = payload.get("access_token")
            expires = int(payload.get("expires_in", 0))
            if not isinstance(token, str) or not token or expires <= 0:
                raise ValueError()
            # A successful code exchange alone does not prove ads_read consent.
            permissions = self.transport.request("/me/permissions", token=token)
            data = permissions.get("data")
            if not isinstance(data, list) or not any(
                isinstance(p, dict) and p.get("permission") == "ads_read" and p.get("status") == "granted"
                for p in data
            ):
                raise MetaLiveOAuthClientError("Meta Ads permission is missing. Reconnect and grant ads_read.")
            return MetaTokenExchangeResult(token, datetime.now(UTC) + timedelta(seconds=expires), ("ads_read",))
        except (MetaReadOnlyClientError, ValueError, TypeError, OverflowError):
            raise MetaLiveOAuthClientError("Meta Ads authorization failed. Reconnect and try again.") from None


def build_meta_oauth_authorization_url(*, authorize_url: str, app_id: str, redirect_uri: str,
                                      state: str, scopes: Sequence[str], config_id: str | None = None) -> str:
    params = {"client_id": app_id, "redirect_uri": redirect_uri, "state": state,
              "response_type": "code", "scope": ",".join(scopes)}
    if config_id:
        params["config_id"] = config_id
    return f"{authorize_url}?{urlencode(params)}"
