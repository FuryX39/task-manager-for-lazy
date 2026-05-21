import secrets
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from .config import APP_TZ
from .models import Category, DayMark, Setting, Task

LINK_CODE_KEY = "telegram_link_code"
LINK_CODE_EXPIRES_KEY = "telegram_link_code_expires"
CHAT_ID_KEY = "telegram_chat_id"

DEFAULT_CATEGORIES = [
    ("Рабочий", "#3d8bfd", 10),
    ("Выходной", "#7fd99a", 20),
    ("Учёба", "#ffb454", 30),
    ("Праздник", "#f07178", 40),
]


def _to_utc_naive(dt: datetime) -> datetime:
    """Принимает naive (как локальное в APP_TZ) или aware datetime и возвращает naive UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=APP_TZ)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def list_tasks(db: Session) -> list[Task]:
    return db.query(Task).order_by(Task.due_at.asc()).all()


def get_task(db: Session, task_id: int) -> Task | None:
    return db.query(Task).filter(Task.id == task_id).first()


def create_task(db: Session, title: str, notes: str | None, due_at: datetime) -> Task:
    task = Task(title=title, notes=notes, due_at=_to_utc_naive(due_at))
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task(db: Session, task: Task, **fields) -> Task:
    for key, value in fields.items():
        if value is None and key not in {"notes"}:
            continue
        if key == "due_at" and value is not None:
            value = _to_utc_naive(value)
            task.last_reminder_at = None
            task.reminder_sent = False
        if key == "completed" and value is True:
            task.reminder_sent = True
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: Task) -> None:
    db.delete(task)
    db.commit()


def get_setting(db: Session, key: str) -> str | None:
    row = db.query(Setting).filter(Setting.key == key).first()
    return row.value if row else None


def set_setting(db: Session, key: str, value: str | None) -> None:
    row = db.query(Setting).filter(Setting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Setting(key=key, value=value))
    db.commit()


def get_chat_id(db: Session) -> str | None:
    return get_setting(db, CHAT_ID_KEY)


def is_telegram_linked(db: Session) -> bool:
    return get_chat_id(db) is not None


def create_link_code(db: Session) -> str:
    code = secrets.token_hex(3).upper()
    expires = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    set_setting(db, LINK_CODE_KEY, code)
    set_setting(db, LINK_CODE_EXPIRES_KEY, expires)
    return code


def verify_and_link(db: Session, code: str, chat_id: str) -> bool:
    stored = get_setting(db, LINK_CODE_KEY)
    expires_raw = get_setting(db, LINK_CODE_EXPIRES_KEY)
    if not stored or not expires_raw:
        return False
    if stored.upper() != code.upper():
        return False
    expires = datetime.fromisoformat(expires_raw)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires:
        return False
    set_setting(db, CHAT_ID_KEY, chat_id)
    set_setting(db, LINK_CODE_KEY, None)
    set_setting(db, LINK_CODE_EXPIRES_KEY, None)
    return True


def tasks_due_for_reminder(
    db: Session, now: datetime, repeat_threshold: datetime
) -> list[Task]:
    return (
        db.query(Task)
        .filter(
            Task.completed.is_(False),
            Task.due_at <= now,
            or_(
                Task.last_reminder_at.is_(None),
                Task.last_reminder_at <= repeat_threshold,
            ),
        )
        .all()
    )


def mark_reminded(db: Session, task: Task, when: datetime) -> None:
    task.last_reminder_at = when
    task.reminder_sent = True
    db.commit()


def complete_task(db: Session, task: Task) -> Task:
    task.completed = True
    task.reminder_sent = True
    db.commit()
    db.refresh(task)
    return task


def snooze_task(db: Session, task: Task, minutes: int) -> Task:
    base = datetime.utcnow()
    task.due_at = base + timedelta(minutes=minutes)
    task.last_reminder_at = None
    task.reminder_sent = False
    db.commit()
    db.refresh(task)
    return task


def bulk_create_tasks(
    db: Session, title: str, notes: str | None, due_ats: list[datetime]
) -> list[Task]:
    created: list[Task] = []
    for due in due_ats:
        task = Task(title=title, notes=notes, due_at=_to_utc_naive(due))
        db.add(task)
        created.append(task)
    db.commit()
    for task in created:
        db.refresh(task)
    return created


def list_categories(db: Session) -> list[Category]:
    return (
        db.query(Category).order_by(Category.sort_order.asc(), Category.id.asc()).all()
    )


def get_category(db: Session, category_id: int) -> Category | None:
    return db.query(Category).filter(Category.id == category_id).first()


def create_category(db: Session, name: str, color: str, sort_order: int) -> Category:
    cat = Category(name=name, color=color, sort_order=sort_order)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def update_category(db: Session, cat: Category, **fields) -> Category:
    for key, value in fields.items():
        if value is None:
            continue
        setattr(cat, key, value)
    db.commit()
    db.refresh(cat)
    return cat


def delete_category(db: Session, cat: Category) -> None:
    db.query(DayMark).filter(DayMark.category_id == cat.id).delete()
    db.delete(cat)
    db.commit()


def seed_default_categories(db: Session) -> None:
    if db.query(Category).count() > 0:
        return
    for name, color, order in DEFAULT_CATEGORIES:
        db.add(Category(name=name, color=color, sort_order=order))
    db.commit()


def list_day_marks(
    db: Session, day_from: date | None, day_to: date | None
) -> list[DayMark]:
    q = db.query(DayMark)
    if day_from:
        q = q.filter(DayMark.day >= day_from)
    if day_to:
        q = q.filter(DayMark.day <= day_to)
    return q.order_by(DayMark.day.asc()).all()


def set_day_mark(db: Session, day: date, category_id: int | None) -> DayMark | None:
    existing = db.query(DayMark).filter(DayMark.day == day).first()
    if category_id is None:
        if existing:
            db.delete(existing)
            db.commit()
        return None
    if existing:
        existing.category_id = category_id
    else:
        existing = DayMark(day=day, category_id=category_id)
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing


def bulk_set_day_marks(
    db: Session, days: list[date], category_id: int | None
) -> list[DayMark]:
    if not days:
        return []
    if category_id is None:
        db.query(DayMark).filter(DayMark.day.in_(days)).delete(synchronize_session=False)
        db.commit()
        return []
    existing = db.query(DayMark).filter(DayMark.day.in_(days)).all()
    by_day = {dm.day: dm for dm in existing}
    result: list[DayMark] = []
    for day in days:
        if day in by_day:
            by_day[day].category_id = category_id
            result.append(by_day[day])
        else:
            dm = DayMark(day=day, category_id=category_id)
            db.add(dm)
            result.append(dm)
    db.commit()
    for dm in result:
        db.refresh(dm)
    return result
