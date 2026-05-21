import asyncio
import logging
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .crud import get_chat_id, is_telegram_linked, verify_and_link
from .database import SessionLocal

logger = logging.getLogger(__name__)

_application: Application | None = None
_main_loop: asyncio.AbstractEventLoop | None = None


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
    logger.info("Запрос /link от chat_id=%s", chat_id)
    db = SessionLocal()
    try:
        ok = verify_and_link(db, code, chat_id)
    finally:
        db.close()
    if ok:
        await update.message.reply_text("Готово! Напоминания о задачах буду присылать сюда.")
    else:
        await update.message.reply_text("Код неверный или истёк. Сгенерируйте новый в веб-интерфейсе.")


def _build_application() -> Application | None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return None
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("link", cmd_link))
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
        # Webhook блокирует polling (частая проблема на VPS)
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


async def _send_message_async(chat_id: str, text: str) -> None:
    if _application is None:
        raise RuntimeError("Telegram-бот не запущен")
    await _application.bot.send_message(chat_id=chat_id, text=text)


def send_reminder(chat_id: str, title: str, notes: str | None, due_at_iso: str) -> bool:
    text = f"Напоминание: {title}\nСрок: {due_at_iso}"
    if notes:
        text += f"\n\n{notes}"

    if _application is None or _main_loop is None:
        logger.warning("Не удалось отправить напоминание: бот не запущен")
        return False

    future = asyncio.run_coroutine_threadsafe(
        _send_message_async(chat_id, text),
        _main_loop,
    )
    future.result(timeout=30)
    return True
