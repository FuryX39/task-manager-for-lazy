"""Мини-миграции по схеме SQLite без alembic."""

import logging

from sqlalchemy import inspect, text

from .database import engine

logger = logging.getLogger(__name__)


def _has_col(insp, table: str, col: str) -> bool:
    return col in {c["name"] for c in insp.get_columns(table)}


def ensure_schema() -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    if "tasks" not in tables:
        return
    with engine.begin() as conn:
        # tasks.last_reminder_at
        if not _has_col(insp, "tasks", "last_reminder_at"):
            conn.execute(text("ALTER TABLE tasks ADD COLUMN last_reminder_at TIMESTAMP"))
            conn.execute(
                text(
                    "UPDATE tasks SET last_reminder_at = CURRENT_TIMESTAMP "
                    "WHERE reminder_sent = 1 AND last_reminder_at IS NULL"
                )
            )
            logger.info("Добавлена колонка tasks.last_reminder_at")

        # user_id в tasks/categories
        insp = inspect(engine)
        if not _has_col(insp, "tasks", "user_id"):
            conn.execute(text("ALTER TABLE tasks ADD COLUMN user_id INTEGER"))
            logger.info("Добавлена колонка tasks.user_id")
        insp = inspect(engine)
        if "categories" in tables and not _has_col(insp, "categories", "user_id"):
            conn.execute(text("ALTER TABLE categories ADD COLUMN user_id INTEGER"))
            logger.info("Добавлена колонка categories.user_id")

        # users: admin/meta колонки
        insp = inspect(engine)
        if "users" in tables and not _has_col(insp, "users", "is_admin"):
            conn.execute(
                text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0 NOT NULL")
            )
            logger.info("Добавлена колонка users.is_admin")
        insp = inspect(engine)
        if "users" in tables and not _has_col(insp, "users", "last_login_at"):
            conn.execute(text("ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP"))
            logger.info("Добавлена колонка users.last_login_at")
        insp = inspect(engine)
        if "users" in tables:
            admin_count = conn.execute(
                text("SELECT COUNT(*) FROM users WHERE is_admin = 1 AND deleted_at IS NULL")
            ).scalar_one()
            if admin_count == 0:
                conn.execute(
                    text(
                        "UPDATE users SET is_admin = 1 "
                        "WHERE id = (SELECT id FROM users WHERE deleted_at IS NULL ORDER BY id LIMIT 1)"
                    )
                )
                logger.info("Назначен первый пользователь администратором")

        # day_marks: раньше PK(day), теперь id PK + user_id + unique(user_id,day)
        insp = inspect(engine)
        if "day_marks" in tables and not _has_col(insp, "day_marks", "id"):
            conn.execute(
                text(
                    """
                    CREATE TABLE day_marks_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        day DATE NOT NULL,
                        category_id INTEGER NOT NULL
                    )
                    """
                )
            )
            old_cols = {c["name"] for c in insp.get_columns("day_marks")}
            if "day" in old_cols and "category_id" in old_cols:
                conn.execute(
                    text(
                        "INSERT INTO day_marks_new(user_id, day, category_id) "
                        "SELECT NULL, day, category_id FROM day_marks"
                    )
                )
            conn.execute(text("DROP TABLE day_marks"))
            conn.execute(text("ALTER TABLE day_marks_new RENAME TO day_marks"))
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_day_marks_user_day "
                    "ON day_marks(user_id, day)"
                )
            )
            logger.info("Таблица day_marks переведена на схему с user_id")
