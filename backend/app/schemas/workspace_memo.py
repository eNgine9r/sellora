from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WorkspaceMemoCreate(BaseModel):
    kind: Literal["NOTE", "TASK"] = "NOTE"
    title: str = Field(min_length=1, max_length=180)
    body: str = Field(default="", max_length=10000)
    due_on: date | None = None
    is_pinned: bool = False

    @model_validator(mode="after")
    def valid_task_fields(self):
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("Title must not be blank")
        if self.kind != "TASK" and self.due_on is not None:
            raise ValueError("Only tasks can have due dates")
        return self


class WorkspaceMemoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    body: str | None = Field(default=None, max_length=10000)
    due_on: date | None = None
    is_pinned: bool | None = None
    is_done: bool | None = None

    @model_validator(mode="after")
    def check_title(self):
        if self.title is not None:
            self.title = self.title.strip()
            if not self.title:
                raise ValueError("Title must not be blank")
        return self


class WorkspaceMemoResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    kind: Literal["NOTE", "TASK"]
    title: str
    body: str
    due_on: date | None
    is_pinned: bool
    is_done: bool
    created_by: UUID | None
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
