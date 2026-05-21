import logging
import os
from datetime import timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

APP_TIMEZONE_NAME = os.getenv("APP_TIMEZONE", "UTC").strip() or "UTC"

try:
    APP_TZ = ZoneInfo(APP_TIMEZONE_NAME)
except ZoneInfoNotFoundError:
    logger.warning(
        "Неизвестный APP_TIMEZONE=%s, используется UTC", APP_TIMEZONE_NAME
    )
    APP_TIMEZONE_NAME = "UTC"
    APP_TZ = timezone.utc

REMINDER_REPEAT_MINUTES = int(os.getenv("REMINDER_REPEAT_MINUTES", "10"))
SNOOZE_MINUTES = int(os.getenv("SNOOZE_MINUTES", "10"))
