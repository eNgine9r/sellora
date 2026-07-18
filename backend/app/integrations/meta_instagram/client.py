from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import httpx

@dataclass
class MetaSendResult:
    provider_request_id: str | None
    provider_message_id: str | None
    raw_status: str

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
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/{self.version}/{instagram_account_id}/messages", params={"access_token": self.access_token}, json=payload)
        response.raise_for_status()
        data = response.json()
        return MetaSendResult(provider_request_id=response.headers.get("x-fb-trace-id"), provider_message_id=data.get("message_id") or data.get("recipient_id"), raw_status="ok")
