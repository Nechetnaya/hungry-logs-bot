from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.services.csv_client import CSVClient
from app.services.logger import log_event

router = Router()
csv_client = CSVClient()

# --- Перезапуск профиля ---
@router.message(F.text == "/restart")
async def restart_profile(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    users = csv_client.get_users()

    # Проверим, есть ли пользователь
    if not any(int(u["user_id"]) == user_id for u in users):
        await message.answer("Ты ещё не зарегистрирован 🙂 Напиши /start, чтобы начать.")
        return

    # Показываем подтверждение удаления
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить профиль", callback_data="confirm_restart")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_restart")]
    ])

    await message.answer(
        "⚠️ Ты уверен, что хочешь удалить свой профиль?\n"
        "Все сохранённые данные будут удалены.",
        reply_markup=markup
    )
    await state.clear()

@router.callback_query(F.data == "confirm_restart")
async def confirm_restart(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    # --- Удаляем пользователя ---
    users = csv_client.get_users()  # читаем всех
    new_users = [u for u in users if int(u["user_id"]) != user_id]  # исключаем текущего
    csv_client.save_users(new_users)  # сохраняем обратно

    # --- Удаляем все записи о приёмах пищи ---
    meals = csv_client.get_meals()
    new_meals = [m for m in meals if int(m.get("user_id", 0)) != user_id]  # оставляем только других пользователей
    csv_client.save_meals(new_meals)  # сохраняем обратно

    # --- Сообщение пользователю ---
    await callback.message.edit_text(
        "✅ Профиль и все записи о приёмах пищи удалены.\n\n"
        "Чтобы начать заново — напиши /start."
    )


@router.callback_query(F.data == "cancel_restart")
async def cancel_restart(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("❌ Перезапуск отменён.")
    log_event("user_restart_cancel", callback.from_user.id)
