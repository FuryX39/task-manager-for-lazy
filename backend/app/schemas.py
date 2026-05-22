from datetime import date, datetime, timezone

from pydantic import BaseModel, Field, field_serializer


def _serialize_utc(v: datetime | None) -> str | None:
    if v is None:
        return None
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v.isoformat()


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

    @field_serializer("due_at", "created_at")
    def _ser_dt(self, v: datetime) -> str:
        return _serialize_utc(v) or ""


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


class DayMarksBulkSet(BaseModel):
    days: list[date] = Field(min_length=1, max_length=1000)
    category_id: int | None = None


class TelegramStatus(BaseModel):
    linked: bool
    link_code: str | None = None


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    has_password: bool
    has_google: bool
    telegram_linked: bool
    is_admin: bool
    created_at: datetime
    last_login_at: datetime | None

    @field_serializer("created_at", "last_login_at")
    def _ser_user_dt(self, v: datetime | None) -> str | None:
        return _serialize_utc(v)


class RegisterRequest(BaseModel):
    email: str
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=200)


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=10)


class DeleteAccountRequest(BaseModel):
    confirm_email: str


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = None
    current_password: str | None = Field(default=None, min_length=1, max_length=200)
    new_password: str | None = Field(default=None, min_length=8, max_length=200)


class AdminUserOut(BaseModel):
    id: int
    email: str
    display_name: str
    is_admin: bool
    has_password: bool
    has_google: bool
    telegram_linked: bool
    created_at: datetime
    last_login_at: datetime | None

    @field_serializer("created_at", "last_login_at")
    def _ser_admin_dt(self, v: datetime | None) -> str | None:
        return _serialize_utc(v)
