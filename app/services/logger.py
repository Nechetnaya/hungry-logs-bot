import logging
from logging.handlers import RotatingFileHandler
import csv
from datetime import datetime
from pathlib import Path

import json

from app.services.telegram_logger import send_telegram_message, TelegramErrorHandler
from app.config import TELEGRAM_CHAT_ID


# === Папка для логов ===
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# === Формат ===
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# === Основной лог ===
main_handler = RotatingFileHandler(
    LOG_DIR / "bot.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
)
main_handler.setFormatter(formatter)

# === Лог ошибок ===
error_handler = RotatingFileHandler(
    LOG_DIR / "errors.log", maxBytes=2_000_000, backupCount=2, encoding="utf-8"
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)

# === Консоль ===
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# === Telegram ошибки ===
telegram_error_handler = TelegramErrorHandler()
telegram_error_handler.setLevel(logging.ERROR)
telegram_error_handler.setFormatter(formatter)

# === Главный логгер ===
logger = logging.getLogger("hungrylogs")
logger.setLevel(logging.INFO)
logger.addHandler(main_handler)
logger.addHandler(error_handler)
logger.addHandler(console_handler)
logger.addHandler(telegram_error_handler)


# === CSV для статистики ===
STATS_FILE = LOG_DIR / "stats.csv"
if not STATS_FILE.exists():
    with STATS_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "event", "user_id", "extra_info"])


def log_event(event: str, user_id: int, extra_info: str = ""):
    """
    Логирует пользовательские события (регистрация, вход, добавление еды и т.д.)
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with STATS_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, event, user_id, extra_info])
    logger.info(f"Event logged: {event} (user_id={user_id}) {extra_info}")
# === CSV для логов модели ===
MODEL_LOG_FILE = LOG_DIR / "model_logs.csv"
if not MODEL_LOG_FILE.exists():
    with MODEL_LOG_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp",      # время запроса
            "user_id",        # ID пользователя
            "input_text",     # текст запроса пользователя
            "json_result",    # JSON с protein/fat/carbs/calories
            "details"         # внутренние детали и предположения
        ])

def log_model_interaction(user_id: int, input_text: str, json_result: dict, details: str = ""):
    """
    Логирует каждый запрос пользователя к модели:
    - пишет в CSV и bot.log
    - дублирует результат в Telegram
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with MODEL_LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            user_id,
            input_text,
            json_result,
            details
        ])
    logger.info(f"Model interaction logged for user_id={user_id}")

    if TELEGRAM_CHAT_ID:
        try:
            message = (
                f"📊 <b>Модель</b>\n\n"
                f"🕒 {timestamp}\n\n"
                f"<b>Запрос:</b>\n{input_text}\n\n"
                f"<b>Результат:</b>\n<pre>{json.dumps(json_result, ensure_ascii=False, indent=2)}</pre>\n\n"
                f"<b>Details:</b>\n{details}"
            )
            send_telegram_message(TELEGRAM_CHAT_ID, message)
        except Exception as e:
            logger.error(f"Ошибка при отправке model log в Telegram: {e}")
