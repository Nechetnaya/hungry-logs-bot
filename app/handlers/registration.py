from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

from app.services.csv_client import CSVClient
from app.services.logger import logger, log_event
from app.services.openai_client import ai_assistant_feedback
from app.services.openai_client import get_user_goal

router = Router()
csv_client = CSVClient()


# --- Состояния ---
class Registration(StatesGroup):
    collecting = State()
    confirm_goal = State()
    set_macros = State()


class UpdateGoal(StatesGroup):
    choose_method = State()
    ai_request = State()
    manual_input = State()
    confirm_new_goal = State()


questions = [
    "Сколько тебе лет?",
    "Какого ты пола?",
    "Какой у тебя рост и вес?",
    "Опиши свой уровень активности в течение дня. Как часто и каким видом спорта ты занимаешься?",
    "Что ты хочешь достичь в первую очередь? Цель по весу?",
    "За какой срок ты хочешь прийти к результату?",
]


# --- Вспомогательные функции ---
def user_exists(user_id: int) -> bool:
    users = csv_client.get_users()
    return any(int(u["user_id"]) == user_id for u in users)


def add_user_profile(user_id: int, profile: dict):
    csv_client.add_user([
        user_id,
        profile.get("age", ""),
        profile.get("sex", ""),
        profile.get("height", ""),
        profile.get("weight", ""),
        profile.get("activity", ""),
        profile.get("goal", ""),
        profile.get("target_cal", ""),
        profile.get("p_goal", ""),
        profile.get("f_goal", ""),
        profile.get("c_goal", "")
    ])
    logger.info(f"👤 [add_user_profile] User {user_id} profile added: {profile}")
    log_event("registration_saved", user_id, extra_info=str(profile.get('goal', '')))

def parse_user_profile(answers_text: str) -> dict:
    return get_user_goal(answers_text)


# --- Старт регистрации ---
@router.message(F.text == "/start")
async def start_registration(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_exists(user_id):
        await message.answer(
            "Ты уже зарегистрирован 🙂\n"
            "Отправь запись о приёме пищи.\n\n"
            "Для просмотра всех команд — введи /help.\n"
            "Удалить профиль и заполнить заново — введи /restart."
        )
        await state.clear()
        return

    await state.set_state(Registration.collecting)
    await state.update_data(answers=[], current=0)
    await message.answer("Привет! Давай познакомимся, чтобы я понял твои цели 💬")
    await message.answer(questions[0])
    print(await state.get_state())

# --- Сбор ответов на вопросы ---
@router.message(Registration.collecting)
async def collect_answers(message: types.Message, state: FSMContext):
    data = await state.get_data()
    answers = data.get("answers", [])
    current = data.get("current", 0)

    answers.append(message.text)
    current += 1
    await state.update_data(answers=answers, current=current)

    if current < len(questions):
        await message.answer(questions[current])
        return

    # все ответы получены
    await message.answer("Спасибо! Обрабатываю твои ответы 🤖...")
    answers_text = "\n".join(
        [f"{i+1}. {q}\n{a}" for i, (q, a) in enumerate(zip(questions, answers))]
    )
    profile = parse_user_profile(answers_text)
    if not profile:
        await message.answer("Не удалось сформировать профиль 😔 Попробуй ещё раз позже.")
        await state.clear()
        return

    await state.update_data(profile=profile)
    await state.set_state(Registration.confirm_goal)

    # инлайн-кнопки для подтверждения или редактирования цели
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ ОК", callback_data="confirm_goal"),
            InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_goal")
        ]
    ])

    await message.answer(
        f"Я определил для тебя такую цель:\n"
        f"Цель: {profile.get('goal', '—')}\n"
        f"Калории: {profile.get('target_cal', '—')} ккал\n"
        f"БЖУ: {profile.get('p_goal', '—')} / {profile.get('f_goal', '—')} / {profile.get('c_goal', '—')}\n\n"
        "Чтобы сохранить цель - нажми 'ОК', чтобы задать цель вручную - нажми 'Изменить'.",
        reply_markup=markup
    )


# --- Callback для сохранения или редактирования ---
@router.callback_query(F.data == "confirm_goal")
async def confirm_goal_callback(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    profile = data.get("profile", {})
    user_id = callback.from_user.id

    await callback.answer()
    if profile:
        add_user_profile(user_id, profile)
        await callback.message.edit_text(
            f"✅ Профиль сохранён!\n\n"
            f"Цель: {profile['goal']}\n"
            f"Калорийность: {profile['target_cal']} ккал\n"
            f"БЖУ: {profile['p_goal']} / {profile['f_goal']} / {profile['c_goal']}"
        )
        await state.clear()
    else:
        await callback.message.edit_text("⚠️ Ошибка: профиль не найден.")


@router.callback_query(F.data == "edit_goal")
async def edit_goal_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await callback.answer()
    await state.set_state(UpdateGoal.manual_input)

    # сообщение с инструкцией и кнопкой отмены
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_goal")]
    ])
    await callback.message.edit_text(
        "Укажи желаемую калорийность и БЖУ через слеш (например 1900/75/100/250)",
        reply_markup=markup
    )


# --- /update_goal: показываем панель выбора ---
@router.message(F.text == "/update_goal")
async def update_goal(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = csv_client.get_user(user_id)
    if not user:
        await message.answer("Сначала нужно зарегистрироваться. Напиши /start")
        return

    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Вручную"), types.KeyboardButton(text="AI-ассистент")],
            [types.KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(
        "Как хочешь обновить цель?\n"
        "1️⃣ Ввести вручную\n"
        "2️⃣ Вызвать AI-ассистента",
        reply_markup=markup
    )

    await state.update_data(profile=user)
    await state.set_state(UpdateGoal.choose_method)
    log_event("goal_update_start", user_id)


# --- Пользователь выбрал способ (панель) ---
@router.message(UpdateGoal.choose_method)
async def handle_goal_update_choice(message: types.Message, state: FSMContext):
    choice = (message.text or "").strip().lower()
    user_id = message.from_user.id

    # Отмена из панели
    if "отмена" in choice or choice == "❌" or choice == "❌ отмена":
        await message.answer("❌ Обновление цели отменено.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        log_event("goal_update_cancel", user_id)
        return

    # Вручную: убираем reply-клавиатуру и просим ввести строку,
    # но даём inline-кнопку для отмены
    if "вручную" in choice:
        await state.set_state(UpdateGoal.manual_input)

        inline_cancel = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_goal")]
        ])

        await message.answer(
            "Укажи желаемую калорийность и БЖУ через слеш (например 1900/75/100/250).",
            reply_markup=ReplyKeyboardRemove()
        )

        # Отдельным сообщением даём inline-кнопку отмены (чтобы была видна всегда)
        await message.answer("Если передумал — нажми кнопку ниже.", reply_markup=inline_cancel)

        log_event("goal_update_manual", user_id)
        return

    # AI-ассистент: убираем reply-клавиатуру и просим пояснение, с inline-кнопкой отмены
    if "ассистент" in choice or "ai" in choice:
        await state.set_state(UpdateGoal.ai_request)

        inline_cancel = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_goal")]
        ])

        await message.answer(
            "🤖 Что ты хочешь изменить в питании?",
            reply_markup=ReplyKeyboardRemove()
        )
        await message.answer("Если передумал — нажми кнопку ниже.", reply_markup=inline_cancel)

        log_event("goal_update_ai", user_id)
        return

    # Если не распознали выбор
    await message.answer(
        "Выбери один из вариантов: 'Вручную', 'AI-ассистент' или 'Отмена'.",
        reply_markup=ReplyKeyboardRemove()
    )


# --- Вручную: парсим ввод пользователя и показываем подтверждение (inline) ---
@router.message(UpdateGoal.manual_input)
async def manual_goal_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = (message.text or "").strip()

    # Если пользователь случайно нажал inline-кнопку "❌ Отменить" ранее,
    # сюда может прийти текст "❌" — обрабатываем как отмену:
    if text == "❌" or "отмена" in text.lower():
        await message.answer("❌ Изменение цели отменено.")
        await state.clear()
        log_event("goal_update_cancel_manual", user_id)
        return

    # Парсим формат
    try:
        parts = [p.strip() for p in text.split("/")]
        if len(parts) != 4:
            raise ValueError("Неверное количество частей")
        target_cal, p_goal, f_goal, c_goal = map(int, parts)
    except Exception:
        await message.answer("⚠️ Неверный формат. Используй формат: 1900/75/100/250")
        logger.warning(f"[manual_goal_input] invalid format from {user_id}: {text}")
        return

    new_goal = {
        "goal": "пользовательская цель",
        "target_cal": target_cal,
        "p_goal": p_goal,
        "f_goal": f_goal,
        "c_goal": c_goal
    }

    # Сохраняем в state для подтверждения
    await state.update_data(pending_goal=new_goal)

    # Показываем подтверждение один раз (только одно сообщение)
    confirm_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять", callback_data="accept_manual_goal"),
         InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_goal")]
    ])

    await message.answer(
        f"🎯 Проверь цель:\n"
        f"🍽 Калории: {new_goal['target_cal']}\n"
        f"💪 Белки: {new_goal['p_goal']}\n"
        f"🥑 Жиры: {new_goal['f_goal']}\n"
        f"🍞 Углеводы: {new_goal['c_goal']}\n\n"
        "Нажми ✅ чтобы сохранить или ❌ чтобы отменить.",
        reply_markup=confirm_markup
    )

    await state.set_state(UpdateGoal.confirm_new_goal)
    log_event("goal_manual_suggested", user_id, extra_info=str(new_goal))


# --- AI: отправляем запрос ИИ, сохраняем результат в state и присылаем подтверждение ---
@router.message(UpdateGoal.ai_request)
async def handle_ai_request(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_request = (message.text or "").strip()

    # Защитная проверка: если пользователь нажал отмену в текстовой форме
    if user_request == "❌" or "отмена" in user_request.lower():
        await message.answer("❌ Изменение цели отменено.")
        await state.clear()
        log_event("goal_update_cancel_ai", user_id)
        return

    # Сообщение-индекатор (не хранить это в state)
    await message.answer("🤖 Анализирую твой рацион и цели...")

    result = await ai_assistant_feedback(user_id, user_request)
    if "error" in result:
        await message.answer(result["error"])
        await state.clear()
        return

    summary = result.get("summary", "")
    g = result.get("new_goal")
    if not g:
        await message.answer("⚠️ ИИ вернул некорректный формат. Попробуй позже.")
        await state.clear()
        return

    # Нормализуем числа в целях (на случай строк)
    try:
        g_normalized = {
            "goal": g.get("goal", "не указано"),
            "target_cal": int(float(g.get("target_cal", 0))),
            "p_goal": int(float(g.get("p_goal", 0))),
            "f_goal": int(float(g.get("f_goal", 0))),
            "c_goal": int(float(g.get("c_goal", 0))),
        }
    except Exception:
        g_normalized = {
            "goal": g.get("goal", "не указано"),
            "target_cal": g.get("target_cal", 0),
            "p_goal": g.get("p_goal", 0),
            "f_goal": g.get("f_goal", 0),
            "c_goal": g.get("c_goal", 0),
        }

    # Сохраняем в state для подтверждения
    await state.update_data(pending_goal=g_normalized)

    confirm_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять", callback_data="accept_goal"),
         InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_goal")]
    ])

    await message.answer(
        f"🤖 {summary}\n\n"
        f"📊 Новая цель (предложение AI):\n"
        f"🎯 {g_normalized['goal'].capitalize()}\n"
        f"🍽 Калории: {g_normalized['target_cal']}\n"
        f"💪 Белки: {g_normalized['p_goal']}\n"
        f"🥑 Жиры: {g_normalized['f_goal']}\n"
        f"🍞 Углеводы: {g_normalized['c_goal']}\n\n"
        "Нажми ✅ чтобы сохранить или ❌ чтобы отменить.",
        reply_markup=confirm_markup
    )

    await state.set_state(UpdateGoal.confirm_new_goal)
    log_event("goal_ai_suggested", user_id, extra_info=str(g_normalized))


# --- Коллбэк: принять цель (AI или ручной) ---
@router.callback_query(F.data.in_(["accept_goal", "accept_manual_goal"]))
async def accept_goal_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()  # убираем "часики" в UI
    data = await state.get_data()
    g = data.get("pending_goal")
    user_id = callback.from_user.id

    if not g:
        # если нет цели в state — информируем и очищаем state
        try:
            await callback.message.answer("⚠️ Ошибка: данные цели не найдены.")
        except Exception:
            pass
        await state.clear()
        return

    # Сохраняем в CSV (оборачиваем в try, логируем)
    try:
        csv_client.update_user_target(user_id, g)
        await callback.message.answer("✅ Новая цель сохранена!")
        logger.info(f"🎯 [accept_goal] Updated goal for {user_id}: {g}")
        log_event("goal_updated", user_id, extra_info=str(g))
    except Exception as e:
        logger.exception(f"[accept_goal] error saving for {user_id}: {e}")
        try:
            await callback.message.answer("❌ Не удалось сохранить цель. Попробуй позже.")
        except Exception:
            pass

    await state.clear()


# --- Коллбэк: отмена (в любом месте с inline-кнопкой) ---
@router.callback_query(F.data == "cancel_goal")
async def cancel_goal_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.edit_text("❌ Изменение цели отменено.")
    except Exception:
        pass
    log_event("goal_update_cancel", callback.from_user.id)
    await state.clear()

