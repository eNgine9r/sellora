from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import httpx

from app.integrations.meta_instagram.exceptions import MetaInstagramError


@dataclass(frozen=True)
class MetaTokenResult:
    access_token: str
    user_id: str | None = None
    expires_at: datetime | None = None
    granted_permissions: list[str] | None = None


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
    async def inspect_account(self, *, access_token: str, token_user_id: str | None = None) -> MetaAccountProfile: ...


class MetaInstagramOAuthClient:
    def __init__(self, *, app_id: str, app_secret: str, token_url: str, graph_base_url: str, graph_version: str, timeout_seconds: float = 10) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.token_url = token_url
        self.graph_base_url = graph_base_url.rstrip("/")
        self.graph_version = graph_version.strip("/")
        self.timeout_seconds = timeout_seconds
        self._last_granted_permissions: list[str] | None = None

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
        permissions = self._permissions_from_payload(payload)
        self._last_granted_permissions = permissions
        return MetaTokenResult(access_token=token, user_id=self._user_id_from_payload(payload), expires_at=self._expires_at(payload.get("expires_in")), granted_permissions=permissions)

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
        permissions = self._permissions_from_payload(payload) or self._last_granted_permissions
        if permissions:
            self._last_granted_permissions = permissions
        return MetaTokenResult(access_token=token, user_id=self._user_id_from_payload(payload), expires_at=self._expires_at(payload.get("expires_in")), granted_permissions=permissions)

    async def inspect_account(self, *, access_token: str, token_user_id: str | None = None) -> MetaAccountProfile:
        headers = {"Authorization": f"Bearer {access_token}"}
        account = await self._profile_request(headers=headers, fields="user_id,username,account_type", stage="profile_primary")
        if account is None:
            account = await self._profile_request(headers=headers, fields="username,account_type", stage="profile_fallback", allow_field_fallback=False)
        instagram_account_id = str(token_user_id or account.get("user_id") or account.get("id") or "")
        if not instagram_account_id:
            raise MetaInstagramError("META_ACCOUNT_IDENTITY_MISSING", "Meta account identity is missing.", 400)
        granted = self._last_granted_permissions
        if granted is None:
            granted = await self._inspect_permissions(access_token=access_token, headers=headers)
        return MetaAccountProfile(
            instagram_account_id=instagram_account_id,
            username=account.get("username"),
            account_type=account.get("account_type"),
            granted_permissions=granted,
        )

    async def _profile_request(self, *, headers: dict[str, str], fields: str, stage: str, allow_field_fallback: bool = True) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(f"{self.graph_base_url}/{self.graph_version}/me", headers=headers, params={"fields": fields})
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            raise MetaInstagramError("META_PROVIDER_UNAVAILABLE", "Meta account profile validation timed out.", 504) from exc
        except httpx.HTTPStatusError as exc:
            if allow_field_fallback and self._is_field_error(exc.response):
                return None
            raise MetaInstagramError("META_ACCOUNT_PROFILE_VALIDATION_FAILED", "Meta account profile validation failed.", 400) from exc

    def _is_field_error(self, response: httpx.Response) -> bool:
        try:
            error = response.json().get("error", {})
        except (AttributeError, ValueError):
            return False
        message = str(error.get("message") or "").lower()
        return response.status_code == 400 and ("field" in message or "unknown" in message or "unsupported" in message)

    async def _inspect_permissions(self, *, access_token: str, headers: dict[str, str]) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                permissions = await client.get(f"{self.graph_base_url}/{self.graph_version}/me/permissions", headers=headers)
            permissions.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MetaInstagramError("META_PROVIDER_UNAVAILABLE", "Meta permission validation timed out.", 504) from exc
        except httpx.HTTPStatusError as exc:
            raise MetaInstagramError("META_PERMISSION_VALIDATION_FAILED", "Meta permission validation failed.", 400) from exc
        permission_payload = permissions.json().get("data", [])
        return [str(item.get("permission")) for item in permission_payload if item.get("status") in {"granted", "approved"} and item.get("permission")]

    def _user_id_from_payload(self, payload: dict[str, Any]) -> str | None:
        value = payload.get("user_id") or payload.get("id")
        return str(value) if value else None

    def _permissions_from_payload(self, payload: dict[str, Any]) -> list[str] | None:
        raw = payload.get("permissions") or payload.get("granted_scopes") or payload.get("scope")
        if raw is None:
            return None
        if isinstance(raw, str):
            values = raw.replace(" ", ",").split(",")
        elif isinstance(raw, list):
            values = raw
        else:
            return None
        permissions = [str(item).strip() for item in values if str(item).strip()]
        return permissions or None

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
