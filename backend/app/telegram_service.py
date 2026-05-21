import asyncio
import logging
import os
from datetime import datetime, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from . import crud
from .config import APP_TZ, SNOOZE_MINUTES
from .database import SessionLocal
from .models import Task

logger = logging.getLogger(__name__)

_application: Application | None = None
_main_loop: asyncio.AbstractEventLoop | None = None


def _format_due(dt: datetime) -> str:
    # В БД хранится naive UTC, добавим зону для корректной конвертации в APP_TZ.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(APP_TZ).strftime("%d.%m.%Y %H:%M")


def _reminder_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Выполнено", callback_data=f"done:{task_id}"),
                InlineKeyboardButton(
                    f"⏰ +{SNOOZE_MINUTES} мин", callback_data=f"snooze:{task_id}"
                ),
            ]
        ]
    )


def _reminder_text(task: Task) -> str:
    text = f"⏰ Напоминание: {task.title}\nСрок: {_format_due(task.due_at)}"
    if task.notes:
        text += f"\n\n{task.notes}"
    return text


async def _on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Ошибка Telegram-бота: %s", context.error)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "Привет! Я напоминаю о задачах из веб-таск-менеджера.\n\n"
        "1. Откройте веб-интерфейс и нажмите «Привязать Telegram».\n"
        "2. Отправьте мне команду: /link КОД\n\n"
        "Команды:\n"
        "/start — эта справка\n"
        "/status — проверить привязку"
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    db = SessionLocal()
    try:
        linked = crud.is_telegram_linked(db)
        chat_id = crud.get_chat_id(db)
    finally:
        db.close()
    if linked and update.effective_chat and str(update.effective_chat.id) == chat_id:
        await update.message.reply_text("Telegram привязан. Напоминания будут приходить сюда.")
    elif linked:
        await update.message.reply_text("Привязка есть, но этот чат не совпадает с сохранённым.")
    else:
        await update.message.reply_text(
            "Telegram ещё не привязан. Используйте /link КОД из веб-интерфейса."
        )


async def cmd_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return
    if not context.args:
        await update.message.reply_text("Укажите код: /link AB12CD")
        return
    code = context.args[0].strip()
    chat_id = str(update.effective_chat.id)
    db = SessionLocal()
    try:
        ok = crud.verify_and_link(db, code, chat_id)
    finally:
        db.close()
    if ok:
        await update.message.reply_text("Готово! Напоминания о задачах буду присылать сюда.")
    else:
        await update.message.reply_text("Код неверный или истёк. Сгенерируйте новый в веб-интерфейсе.")


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()
    data = query.data
    try:
        action, raw_id = data.split(":", 1)
        task_id = int(raw_id)
    except (ValueError, AttributeError):
        return

    db = SessionLocal()
    try:
        task = crud.get_task(db, task_id)
        if not task:
            await query.edit_message_text("Задача не найдена или удалена.")
            return

        if action == "done":
            crud.complete_task(db, task)
            await query.edit_message_text(
                f"✅ Выполнено: {task.title}\nСрок был: {_format_due(task.due_at)}"
            )
        elif action == "snooze":
            crud.snooze_task(db, task, SNOOZE_MINUTES)
            await query.edit_message_text(
                f"⏰ Отложено на {SNOOZE_MINUTES} мин: {task.title}\n"
                f"Новый срок: {_format_due(task.due_at)}"
            )
    finally:
        db.close()


def _build_application() -> Application | None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return None
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("link", cmd_link))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_error_handler(_on_error)
    return app


async def start_telegram_bot() -> None:
    global _application, _main_loop

    if _application is not None:
        return

    _application = _build_application()
    if _application is None:
        logger.warning("TELEGRAM_BOT_TOKEN не задан — бот не запущен")
        return

    _main_loop = asyncio.get_running_loop()

    try:
        await _application.initialize()
        try:
            await _application.bot.delete_webhook(drop_pending_updates=True)
        except Exception:
            logger.exception("Не удалось сбросить webhook (продолжаю)")
        await _application.start()
        await _application.updater.start_polling(drop_pending_updates=True)
        try:
            me = await _application.bot.get_me()
            logger.info("Telegram-бот запущен: @%s (polling)", me.username)
        except Exception:
            logger.info("Telegram-бот запущен (polling)")
    except Exception:
        logger.exception("Telegram-бот не удалось запустить — API продолжает работать")
        _application = None
        _main_loop = None


async def stop_telegram_bot() -> None:
    global _application, _main_loop

    if _application is None:
        return

    if _application.updater.running:
        await _application.updater.stop()
    await _application.stop()
    await _application.shutdown()
    _application = None
    _main_loop = None
    logger.info("Telegram-бот остановлен")


def get_bot_debug_info() -> dict:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    polling = bool(_application and _application.updater.running)
    return {
        "token_configured": bool(token),
        "token_prefix": token[:8] + "..." if len(token) > 8 else None,
        "polling_running": polling,
    }


async def _send_reminder_async(chat_id: str, text: str, keyboard: InlineKeyboardMarkup) -> None:
    assert _application is not None
    await _application.bot.send_message(
        chat_id=chat_id, text=text, reply_markup=keyboard
    )


def send_task_reminder(chat_id: str, task: Task) -> bool:
    if _application is None or _main_loop is None:
        logger.warning("Не удалось отправить напоминание: бот не запущен")
        return False
    text = _reminder_text(task)
    keyboard = _reminder_keyboard(task.id)
    future = asyncio.run_coroutine_threadsafe(
        _send_reminder_async(chat_id, text, keyboard),
        _main_loop,
    )
    future.result(timeout=30)
    return True
