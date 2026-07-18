from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import httpx

from app.integrations.meta_instagram.exceptions import MetaInstagramError


@dataclass(frozen=True)
class MetaTokenResult:
    access_token: str
    expires_at: datetime | None = None


@dataclass(frozen=True)
class MetaAccountProfile:
    instagram_account_id: str
    username: str | None
    account_type: str | None
    granted_permissions: list[str]
    token_expires_at: datetime | None = None


@dataclass
class MetaSendResult:
    provider_request_id: str | None
    provider_message_id: str | None
    raw_status: str


class MetaInstagramOAuthClientProtocol(Protocol):
    async def exchange_code(self, *, code: str, redirect_uri: str) -> MetaTokenResult: ...
    async def exchange_long_lived(self, *, access_token: str) -> MetaTokenResult: ...
    async def inspect_account(self, *, access_token: str) -> MetaAccountProfile: ...


class MetaInstagramOAuthClient:
    def __init__(self, *, app_id: str, app_secret: str, token_url: str, graph_base_url: str, graph_version: str, timeout_seconds: float = 10) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.token_url = token_url
        self.graph_base_url = graph_base_url.rstrip("/")
        self.graph_version = graph_version.strip("/")
        self.timeout_seconds = timeout_seconds

    async def exchange_code(self, *, code: str, redirect_uri: str) -> MetaTokenResult:
        data = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.token_url, data=data)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MetaInstagramError("META_PROVIDER_UNAVAILABLE", "Meta OAuth request timed out.", 504) from exc
        except httpx.HTTPStatusError as exc:
            raise MetaInstagramError("META_OAUTH_STATE_INVALID", "Meta OAuth code exchange failed.", 400) from exc
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise MetaInstagramError("META_TOKEN_INVALID", "Meta OAuth response did not include an access token.", 502)
        return MetaTokenResult(access_token=token, expires_at=self._expires_at(payload.get("expires_in")))

    async def exchange_long_lived(self, *, access_token: str) -> MetaTokenResult:
        params = {"grant_type": "ig_exchange_token", "client_secret": self.app_secret, "access_token": access_token}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(f"{self.graph_base_url}/{self.graph_version}/access_token", params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError:
            return MetaTokenResult(access_token=access_token)
        payload = response.json()
        token = payload.get("access_token") or access_token
        return MetaTokenResult(access_token=token, expires_at=self._expires_at(payload.get("expires_in")))

    async def inspect_account(self, *, access_token: str) -> MetaAccountProfile:
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                me = await client.get(f"{self.graph_base_url}/{self.graph_version}/me", headers=headers, params={"fields": "id,username,account_type"})
                me.raise_for_status()
                permissions = await client.get(f"{self.graph_base_url}/{self.graph_version}/me/permissions", headers=headers)
                permissions.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MetaInstagramError("META_PROVIDER_UNAVAILABLE", "Meta account validation timed out.", 504) from exc
        except httpx.HTTPStatusError as exc:
            raise MetaInstagramError("META_TOKEN_INVALID", "Meta account validation failed.", 400) from exc
        account = me.json()
        permission_payload = permissions.json().get("data", [])
        granted = [str(item.get("permission")) for item in permission_payload if item.get("status") in {"granted", "approved"} and item.get("permission")]
        return MetaAccountProfile(
            instagram_account_id=str(account.get("id") or ""),
            username=account.get("username"),
            account_type=account.get("account_type"),
            granted_permissions=granted,
        )

    def _expires_at(self, expires_in: Any) -> datetime | None:
        try:
            seconds = int(expires_in)
        except (TypeError, ValueError):
            return None
        return datetime.now(UTC) + timedelta(seconds=seconds)


class MetaInstagramClient:
    def __init__(self, base_url: str, version: str, access_token: str, timeout_seconds: float = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.version = version.strip("/")
        self.access_token = access_token
        self.timeout_seconds = timeout_seconds

    async def send_text_message(self, instagram_account_id: str, recipient_scoped_id: str, message_text: str, human_agent: bool = False) -> MetaSendResult:
        payload: dict[str, Any] = {"recipient": {"id": recipient_scoped_id}, "message": {"text": message_text}}
        if human_agent:
            payload["tag"] = "HUMAN_AGENT"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/{self.version}/{instagram_account_id}/messages", headers=headers, json=payload)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MetaInstagramError("META_RECONCILIATION_REQUIRED", "Meta send result is ambiguous after timeout.", 504) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                raise MetaInstagramError("META_PROVIDER_RATE_LIMITED", "Meta provider rate limited the send request.", 429) from exc
            if status >= 500:
                raise MetaInstagramError("META_PROVIDER_UNAVAILABLE", "Meta provider is unavailable.", 503) from exc
            raise MetaInstagramError("META_SEND_DISABLED", "Meta rejected the send request.", 400) from exc
        data = response.json()
        return MetaSendResult(provider_request_id=response.headers.get("x-fb-trace-id"), provider_message_id=data.get("message_id") or data.get("recipient_id"), raw_status="ok")
