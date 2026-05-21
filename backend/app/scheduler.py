import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from . import crud
from .config import REMINDER_REPEAT_MINUTES
from .database import SessionLocal
from .telegram_service import send_task_reminder

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def check_reminders() -> None:
    db = SessionLocal()
    try:
        chat_id = crud.get_chat_id(db)
        if not chat_id:
            return
        # БД хранит naive UTC, сравниваем тоже naive UTC
        now = datetime.utcnow()
        threshold = now - timedelta(minutes=REMINDER_REPEAT_MINUTES)
        due_tasks = crud.tasks_due_for_reminder(db, now, threshold)
        for task in due_tasks:
            try:
                ok = send_task_reminder(chat_id, task)
                if ok:
                    crud.mark_reminded(db, task, now)
                    logger.info("Напоминание отправлено: %s (id=%s)", task.title, task.id)
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
    logger.info(
        "Планировщик напоминаний запущен (проверка каждые 30 сек, повтор каждые %s мин)",
        REMINDER_REPEAT_MINUTES,
    )
