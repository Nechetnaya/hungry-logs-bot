from aiogram import Router, F, types
from aiogram.exceptions import TelegramForbiddenError

from app.config import ADMIN_ID
from app.services.csv_client import CSVClient
from app.services.logger import log_event

router = Router()
csv_client = CSVClient()

@router.message(F.text.startswith("/broadcast"))
async def broadcast_message(message: types.Message):
    """Отправка рассылки всем пользователям из CSV"""
    # Разрешаем команду только админу
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав для этой команды.")
        return

    # Проверяем наличие текста
    text_to_send = message.text[len("/broadcast"):].strip()
    if not text_to_send:
        await message.answer("⚠️ Введите текст после команды. Пример:\n\n`/broadcast Привет, это обновление!`", parse_mode="Markdown")
        return

    await message.answer("🚀 Начинаю рассылку...")

    # Получаем всех пользователей из CSV
    user_ids = csv_client.get_all_user_ids()
    sent = 0
    failed = 0

    for user_id in user_ids:
        try:
            await message.bot.send_message(user_id, text_to_send)
            sent += 1
        except TelegramForbiddenError:
            # Пользователь удалил чат с ботом
            failed += 1
            log_event("broadcast_skip", {"user_id": user_id, "reason": "forbidden"})
        except Exception as e:
            failed += 1
            log_event("broadcast_error", {"user_id": user_id, "error": str(e)})

    await message.answer(f"✅ Рассылка завершена.\n\n📬 Отправлено: {sent}\n🚫 Не доставлено: {failed}")
