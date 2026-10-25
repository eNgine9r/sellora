from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from app.integrations.meta_instagram.exceptions import MetaInstagramError


@dataclass(frozen=True)
class MetaConversationSummary:
    id: str
    updated_time: str | None = None


@dataclass(frozen=True)
class MetaConversationPage:
    conversations: list[MetaConversationSummary]
    after_cursor: str | None = None


@dataclass(frozen=True)
class MetaMessageSummary:
    id: str
    created_time: str | None = None
    is_unsupported: bool = False
    details: MetaMessageDetails | None = None
    details_complete: bool = False


@dataclass(frozen=True)
class MetaMessagePage:
    messages: list[MetaMessageSummary]
    after_cursor: str | None = None


@dataclass(frozen=True)
class MetaMessageDetails:
    id: str
    created_time: str | None
    from_id: str | None
    from_username: str | None
    to: list[dict[str, Any]]
    message: str | None
    is_unsupported: bool
    reply_to_mid: str | None = None
    attachments: list[dict[str, str]] = field(default_factory=list)


class MetaInstagramHistoryClient:
    def __init__(
        self,
        base_url: str,
        version: str,
        access_token: str,
        timeout_seconds: float = 15,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.version = version.strip("/")
        self.access_token = access_token
        self.timeout_seconds = timeout_seconds

    async def list_conversations(
        self,
        instagram_account_id: str,
        *,
        after: str | None = None,
        limit: int = 10,
    ) -> MetaConversationPage:
        params: dict[str, Any] = {
            "platform": "instagram",
            "fields": "id,updated_time",
            "limit": max(1, min(limit, 25)),
        }
        if after:
            params["after"] = after
        payload = await self._get(f"/{instagram_account_id}/conversations", params=params)
        rows = payload.get("data") if isinstance(payload, dict) else None
        conversations = [
            MetaConversationSummary(
                id=str(item.get("id")),
                updated_time=str(item.get("updated_time")) if item.get("updated_time") else None,
            )
            for item in rows or []
            if isinstance(item, dict) and item.get("id")
        ]
        return MetaConversationPage(
            conversations=conversations,
            after_cursor=self._after_cursor(payload),
        )

    async def list_messages(
        self,
        conversation_id: str,
        *,
        after: str | None = None,
        limit: int = 20,
    ) -> MetaMessagePage:
        bounded_limit = max(1, min(limit, 20))
        # Meta may provide message details inline within a conversation. This
        # avoids fetching each older message by its ID, which may be rejected
        # even when the thread and its message IDs remain available.
        rich_fields = f"messages.limit({bounded_limit}){{id,created_time,message,from,to,attachments}}"
        rich_without_media = f"messages.limit({bounded_limit}){{id,created_time,message,from,to}}"
        basic_fields = f"messages.limit({bounded_limit}){{id,created_time}}"
        rich_params = {"fields": rich_fields}
        basic_params = {"fields": basic_fields}
        details_complete = True
        if after:
            # The cursor belongs to the nested messages edge, not the thread object.
            edge_params = {
                "fields": "id,created_time,message,from,to,attachments",
                "limit": bounded_limit, "after": after,
            }
            try:
                payload = await self._get(f"/{conversation_id}/messages", params=edge_params)
            except MetaInstagramError as exc:
                if not self._unsupported_fields_error(exc):
                    raise
                details_complete = False
                try:
                    payload = await self._get(
                        f"/{conversation_id}/messages",
                        params={"fields": "id,created_time,message,from,to", "limit": bounded_limit, "after": after},
                    )
                except MetaInstagramError as fallback_exc:
                    if not self._unsupported_fields_error(fallback_exc):
                        raise
                    payload = await self._get(
                        f"/{conversation_id}/messages",
                        params={"fields": "id,created_time", "limit": bounded_limit, "after": after},
                    )
            messages_payload = payload
        else:
            try:
                payload = await self._get(f"/{conversation_id}", params=rich_params)
            except MetaInstagramError as exc:
                if not self._unsupported_fields_error(exc):
                    raise
                details_complete = False
                try:
                    payload = await self._get(f"/{conversation_id}", params={"fields": rich_without_media})
                except MetaInstagramError as fallback_exc:
                    if not self._unsupported_fields_error(fallback_exc):
                        raise
                    payload = await self._get(f"/{conversation_id}", params=basic_params)
            messages_payload = payload.get("messages") if isinstance(payload, dict) else None
        rows = messages_payload.get("data") if isinstance(messages_payload, dict) else None
        messages = [
            MetaMessageSummary(
                id=str(item["id"]),
                created_time=str(item["created_time"]) if item.get("created_time") else None,
                is_unsupported=bool(item.get("is_unsupported", False)),
                details_complete=details_complete,
                details=self._details_from_payload(item) if (
                    ("from" in item or "to" in item) and
                    (item.get("message") is not None or item.get("is_unsupported") or item.get("attachments"))
                ) else None,
            )
            for item in rows or []
            if isinstance(item, dict) and item.get("id")
        ]
        return MetaMessagePage(
            messages=messages,
            after_cursor=self._after_cursor(messages_payload or {}),
        )

    async def get_message(self, message_id: str) -> MetaMessageDetails:
        # Invalid optional fields (notably reply_to on some Instagram messages)
        # must never cause us to drop otherwise accessible attachment URLs.
        field_sets = (
            "id,created_time,from,to,message,is_unsupported,reply_to,attachments",
            "id,created_time,from,to,message,attachments",
            "id,created_time,from,to,message,is_unsupported,reply_to",
            "id,created_time,from,to,message",
        )
        for fields in field_sets:
            try:
                payload = await self._get(f"/{message_id}", params={"fields": fields})
                break
            except MetaInstagramError as exc:
                if self._unsupported_fields_error(exc):
                    continue
                self._raise_if_unavailable(exc)
                raise
        else:
            # No fields combination was supported; don't report empty content
            # or pretend the provider successfully returned the attachment.
            raise MetaInstagramError(
                "META_HISTORY_ACCESS_DENIED",
                "Meta did not support the requested historical message fields.",
                400,
            )
        return self._details_from_payload(payload, fallback_id=message_id)

    @staticmethod
    def _details_from_payload(payload: dict[str, Any], fallback_id: str = "") -> MetaMessageDetails:
        sender = payload.get("from") if isinstance(payload.get("from"), dict) else {}
        recipients = payload.get("to") if isinstance(payload.get("to"), dict) else {}
        to_data = recipients.get("data") if isinstance(recipients.get("data"), list) else []
        if isinstance(payload.get("to"), list):
            to_data = payload["to"]
        reply_to = payload.get("reply_to") if isinstance(payload.get("reply_to"), dict) else {}
        from app.integrations.meta_instagram.media import normalize_attachments
        provider_attachments = payload.get("attachments")
        if isinstance(provider_attachments, dict):
            provider_attachments = provider_attachments.get("data", [])
        if not isinstance(provider_attachments, list):
            provider_attachments = []
        converted = []
        for entry in provider_attachments:
            if not isinstance(entry, dict):
                continue
            image = entry.get("image_data") or {}
            video = entry.get("video_data") or {}
            media_url = (
                entry.get("file_url") or image.get("url") or video.get("url")
                or (entry.get("payload") or {}).get("url")
            )
            kind = entry.get("type") or ("video" if video else "image")
            converted.append({"type": kind, "payload": {"url": media_url}})
        shared = payload.get("shares")
        if isinstance(shared, dict):
            for entry in shared.get("data", [])[:10]:
                if isinstance(entry, dict):
                    converted.append({"type": "share", "payload": {"link": entry.get("link")}})
        attachments = normalize_attachments({"attachments": converted})
        return MetaMessageDetails(
            id=str(payload.get("id") or fallback_id),
            created_time=str(payload["created_time"]) if payload.get("created_time") else None,
            from_id=str(sender["id"]) if sender.get("id") else None,
            from_username=str(sender["username"]) if sender.get("username") else None,
            to=[item for item in to_data if isinstance(item, dict)],
            message=str(payload["message"]) if payload.get("message") is not None else None,
            is_unsupported=bool(payload.get("is_unsupported", False)),
            reply_to_mid=str(reply_to["mid"]) if reply_to.get("mid") else None,
            attachments=attachments,
        )

    @staticmethod
    def _unsupported_fields_error(exc: MetaInstagramError) -> bool:
        cause = exc.__cause__
        if exc.code != "META_HISTORY_ACCESS_DENIED" or not isinstance(cause, httpx.HTTPStatusError):
            return False
        if cause.response.status_code != 400:
            return False
        try:
            error = cause.response.json().get("error", {})
        except (ValueError, AttributeError):
            return False
        return (isinstance(error, dict) and str(error.get("code")) == "100"
                and "field" in str(error.get("message", "")).lower())

    @staticmethod
    def _raise_if_unavailable(exc: MetaInstagramError) -> None:
        if exc.code != "META_HISTORY_ACCESS_DENIED":
            return
        cause = exc.__cause__
        if not isinstance(cause, httpx.HTTPStatusError):
            return
        try:
            error = cause.response.json().get("error", {})
        except (ValueError, AttributeError):
            error = {}
        code = error.get("code") if isinstance(error, dict) else None
        if cause.response.status_code == 404 or str(code) == "9000001":
            raise MetaInstagramError(
                "META_HISTORY_MESSAGE_UNAVAILABLE",
                "Meta no longer provides this historical message.",
                404,
            ) from exc

    async def _get(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(
                    f"{self.base_url}/{self.version}{path}",
                    headers=headers,
                    params=params,
                )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MetaInstagramError(
                "META_HISTORY_PROVIDER_UNAVAILABLE",
                "Meta history request timed out.",
                504,
            ) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                raise MetaInstagramError(
                    "META_HISTORY_RATE_LIMITED",
                    "Meta rate limited the history request.",
                    429,
                ) from exc
            if status >= 500:
                raise MetaInstagramError(
                    "META_HISTORY_PROVIDER_UNAVAILABLE",
                    "Meta history provider is unavailable.",
                    503,
                ) from exc
            raise MetaInstagramError(
                "META_HISTORY_ACCESS_DENIED",
                "Meta rejected the history request or the item is unavailable.",
                status,
            ) from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise MetaInstagramError(
                "META_HISTORY_PROVIDER_INVALID_RESPONSE",
                "Meta history response was invalid.",
                502,
            ) from exc
        if not isinstance(payload, dict):
            raise MetaInstagramError(
                "META_HISTORY_PROVIDER_INVALID_RESPONSE",
                "Meta history response was invalid.",
                502,
            )
        return payload

    def _after_cursor(self, payload: dict[str, Any]) -> str | None:
        paging = payload.get("paging") if isinstance(payload, dict) else None
        cursors = paging.get("cursors") if isinstance(paging, dict) else None
        after = cursors.get("after") if isinstance(cursors, dict) else None
        return str(after) if after else None
