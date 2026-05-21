"""Мини-миграции по схеме SQLite без alembic."""

import logging

from sqlalchemy import inspect, text

from .database import engine

logger = logging.getLogger(__name__)


def ensure_schema() -> None:
    insp = inspect(engine)
    if "tasks" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("tasks")}
    with engine.begin() as conn:
        if "last_reminder_at" not in cols:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN last_reminder_at TIMESTAMP"))
            # Помечаем уже «отправленные», чтобы они не зазвенели заново
            conn.execute(
                text(
                    "UPDATE tasks SET last_reminder_at = CURRENT_TIMESTAMP "
                    "WHERE reminder_sent = 1 AND last_reminder_at IS NULL"
                )
            )
            logger.info("Добавлена колонка tasks.last_reminder_at")
