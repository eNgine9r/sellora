from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from urllib.parse import urlencode


class MetaLiveOAuthClientError(RuntimeError):
    """Raised when live Meta OAuth token exchange is unavailable or fails safely."""


@dataclass(frozen=True)
class MetaTokenExchangeResult:
    access_token: str
    expires_at: datetime | None = None
    scopes: tuple[str, ...] = ()


class MetaLiveOAuthClientProtocol(Protocol):
    def exchange_code_for_token(self, *, code: str, redirect_uri: str) -> MetaTokenExchangeResult:
        """Exchange an OAuth code for a token. Implementations must be server-only."""


class DisabledMetaLiveOAuthClient:
    def exchange_code_for_token(self, *, code: str, redirect_uri: str) -> MetaTokenExchangeResult:
        raise MetaLiveOAuthClientError("Live Meta token exchange is not implemented.")


def build_meta_oauth_authorization_url(
    *,
    authorize_url: str,
    app_id: str,
    redirect_uri: str,
    state: str,
    scopes: Sequence[str],
) -> str:
    params = {
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "response_type": "code",
        "scope": ",".join(scopes),
    }
    return f"{authorize_url}?{urlencode(params)}"
