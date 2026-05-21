import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from .crud import get_chat_id, mark_reminder_sent, tasks_due_for_reminder
from .database import SessionLocal
from .telegram_service import send_reminder

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _format_due(dt: datetime) -> str:
    if dt.tzinfo:
        local = dt.astimezone()
        return local.strftime("%d.%m.%Y %H:%M")
    return dt.strftime("%d.%m.%Y %H:%M")


def check_reminders() -> None:
    db = SessionLocal()
    try:
        chat_id = get_chat_id(db)
        if not chat_id:
            return
        now = datetime.now(timezone.utc)
        due_tasks = tasks_due_for_reminder(db, now)
        for task in due_tasks:
            try:
                asyncio.run(
                    send_reminder(
                        chat_id,
                        task.title,
                        task.notes,
                        _format_due(task.due_at),
                    )
                )
                mark_reminder_sent(db, task)
                logger.info("Напоминание отправлено: %s", task.title)
            except Exception:
                logger.exception("Не удалось отправить напоминание для задачи %s", task.id)
    finally:
        db.close()


def start_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(check_reminders, "interval", seconds=30, id="reminders")
    _scheduler.start()
    logger.info("Планировщик напоминаний запущен (каждые 30 сек)")
