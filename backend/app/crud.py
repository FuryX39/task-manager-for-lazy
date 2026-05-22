import secrets
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from .config import APP_TZ
from .models import Category, DayMark, Task, User

DEFAULT_CATEGORIES = [
    ("Рабочий", "#3d8bfd", 10),
    ("Выходной", "#7fd99a", 20),
    ("Учёба", "#ffb454", 30),
    ("Праздник", "#f07178", 40),
]


def _to_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=APP_TZ)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def get_user_by_email(db: Session, email: str) -> User | None:
    return (
        db.query(User)
        .filter(User.email == email, User.deleted_at.is_(None))
        .first()
    )


def get_user_by_google_sub(db: Session, sub: str) -> User | None:
    return (
        db.query(User)
        .filter(User.google_sub == sub, User.deleted_at.is_(None))
        .first()
    )


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()


def create_user(
    db: Session,
    email: str,
    display_name: str,
    password_hash: str | None = None,
    google_sub: str | None = None,
    is_admin: bool = False,
) -> User:
    user = User(
        email=email,
        display_name=display_name,
        password_hash=password_hash,
        google_sub=google_sub,
        is_admin=is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, **fields) -> User:
    for key, value in fields.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def touch_last_login(db: Session, user: User) -> User:
    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


def list_active_users(db: Session) -> list[User]:
    return (
        db.query(User)
        .filter(User.deleted_at.is_(None))
        .order_by(User.created_at.asc())
        .all()
    )


def list_users_with_chat(db: Session) -> list[User]:
    return (
        db.query(User)
        .filter(User.deleted_at.is_(None), User.telegram_chat_id.is_not(None))
        .all()
    )


def get_user_by_chat_id(db: Session, chat_id: str) -> User | None:
    return (
        db.query(User)
        .filter(User.telegram_chat_id == chat_id, User.deleted_at.is_(None))
        .first()
    )


def count_users(db: Session) -> int:
    return db.query(User).filter(User.deleted_at.is_(None)).count()


def migrate_legacy_data_to_first_user(db: Session, user_id: int) -> None:
    db.query(Task).filter(Task.user_id.is_(None)).update(
        {Task.user_id: user_id}, synchronize_session=False
    )
    db.query(Category).filter(Category.user_id.is_(None)).update(
        {Category.user_id: user_id}, synchronize_session=False
    )
    db.query(DayMark).filter(DayMark.user_id.is_(None)).update(
        {DayMark.user_id: user_id}, synchronize_session=False
    )
    db.commit()


def list_tasks(db: Session, user_id: int) -> list[Task]:
    return (
        db.query(Task)
        .filter(Task.user_id == user_id)
        .order_by(Task.due_at.asc())
        .all()
    )


def get_task(db: Session, user_id: int, task_id: int) -> Task | None:
    return (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == user_id)
        .first()
    )


def get_task_any(db: Session, task_id: int) -> Task | None:
    return db.query(Task).filter(Task.id == task_id).first()


def create_task(
    db: Session,
    user_id: int,
    title: str,
    notes: str | None,
    due_at: datetime,
) -> Task:
    task = Task(user_id=user_id, title=title, notes=notes, due_at=_to_utc_naive(due_at))
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


def tasks_due_for_reminder(
    db: Session,
    user_id: int,
    now: datetime,
    repeat_threshold: datetime,
) -> list[Task]:
    return (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
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
    db: Session,
    user_id: int,
    title: str,
    notes: str | None,
    due_ats: list[datetime],
) -> list[Task]:
    created: list[Task] = []
    for due in due_ats:
        task = Task(
            user_id=user_id,
            title=title,
            notes=notes,
            due_at=_to_utc_naive(due),
        )
        db.add(task)
        created.append(task)
    db.commit()
    for task in created:
        db.refresh(task)
    return created


def list_categories(db: Session, user_id: int) -> list[Category]:
    return (
        db.query(Category)
        .filter(Category.user_id == user_id)
        .order_by(Category.sort_order.asc(), Category.id.asc())
        .all()
    )


def get_category(db: Session, user_id: int, category_id: int) -> Category | None:
    return (
        db.query(Category)
        .filter(Category.id == category_id, Category.user_id == user_id)
        .first()
    )


def create_category(
    db: Session, user_id: int, name: str, color: str, sort_order: int
) -> Category:
    cat = Category(user_id=user_id, name=name, color=color, sort_order=sort_order)
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


def seed_default_categories(db: Session, user_id: int) -> None:
    if db.query(Category).filter(Category.user_id == user_id).count() > 0:
        return
    for name, color, order in DEFAULT_CATEGORIES:
        db.add(Category(user_id=user_id, name=name, color=color, sort_order=order))
    db.commit()


def list_day_marks(
    db: Session, user_id: int, day_from: date | None, day_to: date | None
) -> list[DayMark]:
    q = db.query(DayMark).filter(DayMark.user_id == user_id)
    if day_from:
        q = q.filter(DayMark.day >= day_from)
    if day_to:
        q = q.filter(DayMark.day <= day_to)
    return q.order_by(DayMark.day.asc()).all()


def set_day_mark(
    db: Session, user_id: int, day: date, category_id: int | None
) -> DayMark | None:
    existing = (
        db.query(DayMark)
        .filter(DayMark.user_id == user_id, DayMark.day == day)
        .first()
    )
    if category_id is None:
        if existing:
            db.delete(existing)
            db.commit()
        return None
    if existing:
        existing.category_id = category_id
    else:
        existing = DayMark(user_id=user_id, day=day, category_id=category_id)
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing


def bulk_set_day_marks(
    db: Session, user_id: int, days: list[date], category_id: int | None
) -> list[DayMark]:
    if not days:
        return []
    if category_id is None:
        (
            db.query(DayMark)
            .filter(DayMark.user_id == user_id, DayMark.day.in_(days))
            .delete(synchronize_session=False)
        )
        db.commit()
        return []
    existing = (
        db.query(DayMark)
        .filter(DayMark.user_id == user_id, DayMark.day.in_(days))
        .all()
    )
    by_day = {dm.day: dm for dm in existing}
    result: list[DayMark] = []
    for day in days:
        if day in by_day:
            by_day[day].category_id = category_id
            result.append(by_day[day])
        else:
            dm = DayMark(user_id=user_id, day=day, category_id=category_id)
            db.add(dm)
            result.append(dm)
    db.commit()
    for dm in result:
        db.refresh(dm)
    return result


def is_telegram_linked(user: User) -> bool:
    return user.telegram_chat_id is not None


def create_link_code_for_user(db: Session, user: User) -> str:
    code = secrets.token_hex(3).upper()
    user.telegram_link_code = code
    user.telegram_link_expires_at = datetime.utcnow() + timedelta(minutes=15)
    db.commit()
    db.refresh(user)
    return code


def verify_and_link_by_code(db: Session, code: str, chat_id: str) -> User | None:
    user = (
        db.query(User)
        .filter(
            User.telegram_link_code == code.upper(),
            User.deleted_at.is_(None),
        )
        .first()
    )
    if not user:
        return None
    if not user.telegram_link_expires_at or user.telegram_link_expires_at < datetime.utcnow():
        return None
    taken = (
        db.query(User)
        .filter(
            User.telegram_chat_id == chat_id,
            User.id != user.id,
            User.deleted_at.is_(None),
        )
        .first()
    )
    if taken:
        return None
    user.telegram_chat_id = chat_id
    user.telegram_link_code = None
    user.telegram_link_expires_at = None
    db.commit()
    db.refresh(user)
    return user


def unlink_telegram(db: Session, user: User) -> User:
    user.telegram_chat_id = None
    user.telegram_link_code = None
    user.telegram_link_expires_at = None
    db.commit()
    db.refresh(user)
    return user


def delete_account_cascade(db: Session, user: User) -> None:
    db.query(Task).filter(Task.user_id == user.id).delete(synchronize_session=False)
    db.query(DayMark).filter(DayMark.user_id == user.id).delete(synchronize_session=False)
    db.query(Category).filter(Category.user_id == user.id).delete(synchronize_session=False)
    user.deleted_at = datetime.utcnow()
    user.telegram_chat_id = None
    user.telegram_link_code = None
    user.telegram_link_expires_at = None
    user.password_hash = None
    user.google_sub = None
    user.display_name = "Deleted user"
    user.email = f"deleted-{user.id}-{int(datetime.utcnow().timestamp())}@deleted.local"
    db.commit()
