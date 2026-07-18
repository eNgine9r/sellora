from typing import Any
from pydantic import BaseModel, Field

class WebhookPersistResult(BaseModel):
    accepted: bool
    event_id: str | None = None
    status: str

class InstagramWebhookEntry(BaseModel):
    id: str | None = None
    time: int | None = None
    messaging: list[dict[str, Any]] = Field(default_factory=list)
