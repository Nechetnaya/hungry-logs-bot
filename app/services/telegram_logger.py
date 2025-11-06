import requests
import logging
import json
from datetime import datetime
from app.config import TELEGRAM_TOKEN_TEST, TELEGRAM_CHAT_ID


def send_telegram_message(chat_id: int, text: str):
    """
    Отправка сообщения в Telegram через Bot API.
    Безопасная, с защитой от таймаутов.
    """
    if not TELEGRAM_TOKEN_TEST or chat_id == 0:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN_TEST}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[TelegramLogger] Ошибка при отправке сообщения: {e}")


class TelegramErrorHandler(logging.Handler):
    """
    Логгер для ошибок: автоматически пересылает ошибки в Telegram.
    """
    def emit(self, record):
        try:
            log_entry = self.format(record)
            message = f"🚨 <b>Ошибка:</b>\n<pre>{log_entry}</pre>"
            send_telegram_message(TELEGRAM_CHAT_ID, message)
        except Exception as e:
            print(f"[TelegramErrorHandler] Ошибка при обработке: {e}")

