import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from .models import Setting, Task

LINK_CODE_KEY = "telegram_link_code"
LINK_CODE_EXPIRES_KEY = "telegram_link_code_expires"
CHAT_ID_KEY = "telegram_chat_id"


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
