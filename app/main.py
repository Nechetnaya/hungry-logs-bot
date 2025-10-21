# main.py
from aiogram import Bot, Dispatcher, types, F
import asyncio
from datetime import date

from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import TELEGRAM_TOKEN
from app.services.csv_client import CSVClient
from app.handlers import registration
from app.services.openai_client import parse_meal_text


bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
csv_client = CSVClient()

# Подключаем роутер регистрации
dp.include_router(registration.router)


@dp.message(StateFilter(None), F.text & ~F.text.startswith("/"))
async def add_meal_handler(message: types.Message, state: FSMContext):
    # Если пользователь в процессе регистрации — не обрабатываем meal
    current_state = await state.get_state()
    if current_state is not None:
        return  # FSM-хендлер обработает сообщение

    user_id = message.from_user.id
    if not csv_client.user_exists(user_id):
        await message.answer("Сначала нужно зарегистрироваться. Напиши /start")
        return

    # Получаем предыдущий неполный ввод, если был
    data = await state.get_data()
    pending = data.get("pending_meal", "")

    meal_text = (pending + " " + message.text).strip() if pending else message.text

    # --- показываем пользователю, что бот думает ---
    thinking_message = await message.answer("🤖 Разбираю приём пищи, ищу калории и БЖУ...")

    parsed = await parse_meal_text(meal_text, user_id)

    if parsed.get("clarification"):
        # Сохраняем неполный ввод и просим уточнение
        await state.update_data(pending_meal=meal_text)
        await message.answer(f"🤔 Я не совсем понял. {parsed['clarification']}")
        return
    else:
        # Успешно разобрали — очищаем pending
        await state.update_data(pending_meal="")

    # Сохраняем приём пищи
    csv_client.add_meal([
        user_id,
        parsed.get("date"),
        meal_text,
        parsed.get("protein", 0),
        parsed.get("fat", 0),
        parsed.get("carbs", 0),
        parsed.get("calories", 0)
    ])

    # Получаем прогресс за день
    total = csv_client.get_daily_totals(user_id, parsed.get("date"))
    user_profile = csv_client.get_user(user_id)

    text = (
        f"✅ Записано\\! Приём: *{int(parsed.get('calories', 0))} ккал*, "
        f"*{int(parsed.get('protein', 0))}/{int(parsed.get('fat', 0))}/{int(parsed.get('carbs', 0))}* БЖУ\n\n"
        f"📊 Итог за день:\n"
        f"Калории: *{int(total['calories'])}* / {user_profile['target_cal']}\n"
        f"Белки: *{int(total['protein'])}* / {user_profile['p_goal']}\n"
        f"Жиры: *{int(total['fat'])}* / {user_profile['f_goal']}\n"
        f"Углеводы: *{int(total['carbs'])}* / {user_profile['c_goal']}"
    )
    await thinking_message.edit_text(text, parse_mode="MarkdownV2")



# --- Запуск бота ---
async def main():
    print("🤖 Bot started.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
