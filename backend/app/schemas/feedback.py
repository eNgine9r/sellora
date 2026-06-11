from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.pilot_feedback import PilotFeedbackCategory, PilotFeedbackStatus


class PilotFeedbackCreate(BaseModel):
    category: PilotFeedbackCategory
    rating: int | None = Field(default=None, ge=1, le=5)
    message: str = Field(min_length=3, max_length=4000)
    page_path: str | None = Field(default=None, max_length=1000)


class PilotFeedbackUpdate(BaseModel):
    status: PilotFeedbackStatus


class PilotFeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: PilotFeedbackCategory
    rating: int | None = None
    message: str
    page_path: str | None = None
    status: PilotFeedbackStatus
    created_at: datetime
    updated_at: datetime
    user_id: UUID | None = None
