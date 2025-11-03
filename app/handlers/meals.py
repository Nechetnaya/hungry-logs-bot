from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
import re

from app.services.csv_client import CSVClient
from app.services.openai_client import parse_meal_text
from app.services.logger import logger, log_event, log_model_interaction

router = Router()
csv_client = CSVClient()


# >>> функция экранирования MarkdownV2
def escape_md_v2(text: str) -> str:
    """
    Экранирует спецсимволы для MarkdownV2.
    """
    if not isinstance(text, str):
        text = str(text)
    return re.sub(r'([\\\[\]\(\)~`>#+\-=|{}.!])', r'\\\1', text)


@router.message(StateFilter(None), F.text & ~F.text.startswith("/") & ~F.text.in_({"За день","За неделю","За 4 недели"}))
async def add_meal_handler(message: types.Message, state: FSMContext):
    # Если пользователь находится в процессе регистрации — не обрабатываем сообщение
    if await state.get_state() is not None:
        return

    user_id = message.from_user.id
    if not csv_client.user_exists(user_id):
        await message.answer("Сначала нужно зарегистрироваться. Напиши /start")
        logger.info(f"🚫 Пользователь {user_id} попытался добавить meal без регистрации")
        return

    data = await state.get_data()
    pending = data.get("pending_meal", "")
    meal_text = (pending + " " + message.text).strip() if pending else message.text

    thinking_message = await message.answer("🤖 Разбираю приём пищи, ищу калории и БЖУ...")

    parsed = await parse_meal_text(meal_text, user_id)

    if parsed.get("clarification"):
        logger.info(f"⚠️ parse_meal_text вернул clarification для user {user_id}: '{meal_text}'")
        log_event("meal_parsed_with_clarification", user_id, extra_info=str(parsed.get("clarification")))
        await state.update_data(pending_meal="")

    else:
        await state.update_data(pending_meal="")

# >>> NEW: подготовим публичную часть результата для хранения и отправки пользователю
# безопасно достаём числовые значения с fallback=0
    try:
        protein = int(float(parsed.get("protein", 0) or 0))
    except Exception:
        protein = 0
    try:
        fat = int(float(parsed.get("fat", 0) or 0))
    except Exception:
        fat = 0
    try:
        carbs = int(float(parsed.get("carbs", 0) or 0))
    except Exception:
        carbs = 0
    try:
        calories = int(float(parsed.get("calories", 0) or 0))
    except Exception:
        calories = 0

# >>> NEW: логирование взаимодействия с моделью (сохраняем детали в отдельный лог-файл)
# предполагается, что parse_meal_text возвращает поле "details" с внутренними допущениями / источниками
    details = parsed.get("details", "")
    public_result = {
        "protein": protein,
        "fat": fat,
        "carbs": carbs,
        "calories": calories,
        "date": parsed.get("date")
    }
    try:
# log_model_interaction записывает в CSV и/или лог-файл (реализация в app.services.logger)
        log_model_interaction(user_id, meal_text, public_result, details)
        logger.info(f"Model interaction logged for user {user_id}")
    except Exception as e:
        logger.exception(f"[log_model_interaction] failed for user {user_id}: {e}")

    # Сохраняем приём пищи
    csv_client.add_meal([
        user_id,
        parsed.get("date"),
        meal_text,
        protein,
        fat,
        carbs,
        calories
    ])
    logger.info(f"✅ Пользователь {user_id} добавил приём пищи: {meal_text}")
    log_event("meal_added", user_id)

    total = csv_client.get_daily_totals(user_id, parsed.get("date"))
    user_profile = csv_client.get_user(user_id)


    text = (
            f"✅ Записано! *{int(parsed.get('calories', 0))} ккал*, "
            f"*{int(parsed.get('protein', 0))}/{int(parsed.get('fat', 0))}/{int(parsed.get('carbs', 0))} БЖУ*\n\n"
            f"📊 Итого за день:\n"
            f"Калории: *{int(total['calories'])}* / {user_profile['target_cal']}\n"
            f"Белки: *{int(total['protein'])}* / {user_profile['p_goal']}\n"
            f"Жиры: *{int(total['fat'])}* / {user_profile['f_goal']}\n"
            f"Углеводы: *{int(total['carbs'])}* / {user_profile['c_goal']}"
        )
    safe_text = escape_md_v2(text)
    await thinking_message.edit_text(safe_text, parse_mode="MarkdownV2")
