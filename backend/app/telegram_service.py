import logging
import os
import threading

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .crud import get_chat_id, is_telegram_linked, verify_and_link
from .database import SessionLocal

logger = logging.getLogger(__name__)

_bot_thread: threading.Thread | None = None


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
        linked = is_telegram_linked(db)
        chat_id = get_chat_id(db)
    finally:
        db.close()
    if linked and update.effective_chat and str(update.effective_chat.id) == chat_id:
        await update.message.reply_text("Telegram привязан. Напоминания будут приходить сюда.")
    elif linked:
        await update.message.reply_text("Привязка есть, но этот чат не совпадает с сохранённым.")
    else:
        await update.message.reply_text("Telegram ещё не привязан. Используйте /link КОД из веб-интерфейса.")


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
        ok = verify_and_link(db, code, chat_id)
    finally:
        db.close()
    if ok:
        await update.message.reply_text("Готово! Напоминания о задачах буду присылать сюда.")
    else:
        await update.message.reply_text("Код неверный или истёк. Сгенерируйте новый в веб-интерфейсе.")


def _run_polling(token: str) -> None:
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("link", cmd_link))
    application.run_polling(drop_pending_updates=True)


def start_telegram_bot() -> None:
    global _bot_thread
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN не задан — бот не запущен")
        return
    if _bot_thread and _bot_thread.is_alive():
        return
    _bot_thread = threading.Thread(
        target=_run_polling,
        args=(token,),
        daemon=True,
        name="telegram-bot",
    )
    _bot_thread.start()
    logger.info("Telegram-бот запущен")


async def send_reminder(chat_id: str, title: str, notes: str | None, due_at_iso: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return False
    app = Application.builder().token(token).build()
    text = f"Напоминание: {title}\nСрок: {due_at_iso}"
    if notes:
        text += f"\n\n{notes}"
    async with app:
        await app.bot.send_message(chat_id=chat_id, text=text)
    return True
