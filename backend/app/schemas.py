from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    notes: str | None = None
    due_at: datetime


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    notes: str | None = None
    due_at: datetime | None = None
    completed: bool | None = None


class TaskOut(BaseModel):
    id: int
    title: str
    notes: str | None
    due_at: datetime
    completed: bool
    reminder_sent: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TelegramStatus(BaseModel):
    linked: bool
    link_code: str | None = None
