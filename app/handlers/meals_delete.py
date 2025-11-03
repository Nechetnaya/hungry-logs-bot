from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.services.csv_client import CSVClient
from app.services.logger import log_event

router = Router()
csv_client = CSVClient()


# --- Шаг 1: команда /delete_last_meal ---
@router.message(F.text == "/delete_last_meal")
async def delete_last_meal(message: types.Message):
    user_id = message.from_user.id
    meals_all = csv_client.get_meals()

    # Индексы всех приёмов этого пользователя в общем списке
    user_indices = [i for i, m in enumerate(meals_all) if int(m.get("user_id", 0)) == user_id]

    if not user_indices:
        await message.answer("⚠️ Нет внесённых приёмов пищи для удаления.")
        return

    last_idx = user_indices[-1]
    last_meal = meals_all[last_idx]

    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Удалить", callback_data=f"confirm_delete:{last_idx}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")]
    ])

    await message.answer(
        f"Удалить последний прием пиши?:\n"
        f"'{last_meal.get('meal_text','—')}' — {last_meal.get('calories','0')} ккал, "
        f"{last_meal.get('protein','0')}/{last_meal.get('fat','0')}/{last_meal.get('carbs','0')} БЖУ?",
        reply_markup=inline_kb
    )
    log_event("delete_last_meal_prompt", user_id, extra_info=str(last_meal))


# --- Шаг 2: подтверждение удаления по индексу ---
@router.callback_query(F.data.startswith("confirm_delete:"))
async def confirm_delete(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    # парсим индекс из callback_data
    try:
        idx = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("⚠️ Неверные данные подтверждения.")
        return

    meals_all = csv_client.get_meals()

    # Если индекс вышел за пределы — найдём последний элемент пользователя
    if idx < 0 or idx >= len(meals_all) or int(meals_all[idx].get("user_id", -1)) != user_id:
        # fallback — удаляем последний приём пользователя если он есть
        user_indices = [i for i, m in enumerate(meals_all) if int(m.get("user_id", 0)) == user_id]
        if not user_indices:
            await callback.message.edit_text("⚠️ Нет внесённых приёмов пищи для удаления.")
            await callback.answer()
            return
        idx = user_indices[-1]

    last_meal = meals_all[idx]

    # удаляем запись с индексом idx
    new_meals = [m for i, m in enumerate(meals_all) if i != idx]
    csv_client.save_meals(new_meals)

    await callback.message.edit_text(f"✅ Последний приём пищи '{last_meal.get('meal_text','—')}' удалён.")
    log_event("delete_last_meal", user_id, extra_info=str(last_meal))
    await callback.answer()


# --- Отмена ---
@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Удаление отменено.")
    log_event("delete_last_meal_cancel", callback.from_user.id)
    await callback.answer()
