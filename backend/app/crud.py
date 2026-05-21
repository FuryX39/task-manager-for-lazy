import secrets
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

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


def list_tasks(db: Session) -> list[Task]:
    return db.query(Task).order_by(Task.due_at.asc()).all()


def get_task(db: Session, task_id: int) -> Task | None:
    return db.query(Task).filter(Task.id == task_id).first()


def create_task(db: Session, title: str, notes: str | None, due_at: datetime) -> Task:
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)
    task = Task(title=title, notes=notes, due_at=due_at)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task(db: Session, task: Task, **fields) -> Task:
    for key, value in fields.items():
        if value is None:
            continue
        if key == "due_at" and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
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


def tasks_due_for_reminder(db: Session, now: datetime) -> list[Task]:
    return (
        db.query(Task)
        .filter(
            Task.completed.is_(False),
            Task.reminder_sent.is_(False),
            Task.due_at <= now,
        )
        .all()
    )


def mark_reminder_sent(db: Session, task: Task) -> None:
    task.reminder_sent = True
    db.commit()


def bulk_create_tasks(
    db: Session, title: str, notes: str | None, due_ats: list[datetime]
) -> list[Task]:
    created: list[Task] = []
    for due in due_ats:
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        task = Task(title=title, notes=notes, due_at=due)
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
