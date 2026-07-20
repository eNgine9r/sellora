from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.integrations.meta_instagram.exceptions import MetaInstagramError


PROFILE_FIELDS = (
    "name,username,profile_pic,follower_count,is_verified_user,"
    "is_user_follow_business,is_business_follow_user"
)


@dataclass(frozen=True)
class InstagramParticipantProfileResult:
    participant_scoped_id: str
    name: str | None
    username: str | None
    profile_picture_url: str | None
    follower_count: int | None
    is_verified_user: bool | None
    is_user_follow_business: bool | None
    is_business_follow_user: bool | None
    provider_request_id: str | None = None


class InstagramParticipantProfileClientProtocol(Protocol):
    def fetch_profile(self, participant_scoped_id: str) -> InstagramParticipantProfileResult: ...


class InstagramParticipantProfileClient:
    def __init__(
        self,
        base_url: str,
        version: str,
        access_token: str,
        timeout_seconds: float = 8,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.version = version.strip("/")
        self.access_token = access_token
        self.timeout_seconds = timeout_seconds

    def fetch_profile(self, participant_scoped_id: str) -> InstagramParticipantProfileResult:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {"fields": PROFILE_FIELDS}
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(
                    f"{self.base_url}/{self.version}/{participant_scoped_id}",
                    headers=headers,
                    params=params,
                )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MetaInstagramError(
                "META_PARTICIPANT_PROFILE_TIMEOUT",
                "Instagram participant profile request timed out.",
                504,
            ) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                raise MetaInstagramError(
                    "META_PARTICIPANT_PROFILE_RATE_LIMITED",
                    "Meta rate limited participant profile enrichment.",
                    429,
                ) from exc
            if status >= 500:
                raise MetaInstagramError(
                    "META_PARTICIPANT_PROFILE_PROVIDER_UNAVAILABLE",
                    "Meta participant profile provider is unavailable.",
                    503,
                ) from exc
            raise MetaInstagramError(
                "META_PARTICIPANT_PROFILE_UNAVAILABLE",
                "Instagram participant profile is unavailable for this conversation.",
                409,
            ) from exc

        payload = response.json()
        if not isinstance(payload, dict):
            raise MetaInstagramError(
                "META_PARTICIPANT_PROFILE_INVALID",
                "Meta returned an invalid participant profile response.",
                502,
            )

        return InstagramParticipantProfileResult(
            participant_scoped_id=participant_scoped_id,
            name=self._text(payload.get("name")),
            username=self._text(payload.get("username")),
            profile_picture_url=self._text(payload.get("profile_pic")),
            follower_count=self._integer(payload.get("follower_count")),
            is_verified_user=self._boolean(payload.get("is_verified_user")),
            is_user_follow_business=self._boolean(payload.get("is_user_follow_business")),
            is_business_follow_user=self._boolean(payload.get("is_business_follow_user")),
            provider_request_id=response.headers.get("x-fb-trace-id"),
        )

    def _text(self, value: Any) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None

    def _integer(self, value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _boolean(self, value: Any) -> bool | None:
        return value if isinstance(value, bool) else None
