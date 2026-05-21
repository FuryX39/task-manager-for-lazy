from datetime import date, datetime

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


class BulkTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    notes: str | None = None
    due_ats: list[datetime] = Field(min_length=1, max_length=1000)


class BulkTaskResult(BaseModel):
    created: int
    tasks: list[TaskOut]


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str = Field(min_length=3, max_length=20)
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, min_length=3, max_length=20)
    sort_order: int | None = None


class CategoryOut(BaseModel):
    id: int
    name: str
    color: str
    sort_order: int

    model_config = {"from_attributes": True}


class DayMarkOut(BaseModel):
    day: date
    category_id: int

    model_config = {"from_attributes": True}


class DayMarkSet(BaseModel):
    category_id: int | None = None


class TelegramStatus(BaseModel):
    linked: bool
    link_code: str | None = None
