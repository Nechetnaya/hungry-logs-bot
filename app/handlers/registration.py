from aiogram import Router, types, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from app.services.csv_client import CSVClient
from app.services.openai_client import get_user_goal

router = Router()
csv_client = CSVClient()

class Registration(StatesGroup):
    collecting = State()
    confirm_goal = State()
    set_macros = State()

questions = [
    "Сколько тебе лет?",
    "Какого ты пола?",
    "Какой у тебя рост и вес?",
    "Опиши свой уровень активности в течение дня? Как часто и каким видом спорта ты занимаешься?",
    "Что ты хочешь достичь в первую очередь? Есть ли конкретная цель по весу или внешнему виду?",
    "За какой срок ты хочешь прийти к результату?",
]

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

def parse_user_profile(answers_text: str) -> dict:
    return get_user_goal(answers_text)

# --- Старт регистрации ---
@router.message(F.text == "/start")
async def start_registration(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_exists(user_id):
        await message.answer("Ты уже зарегистрирован 🙂\nОтправь запись о приёме пищи или введи /help")
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
    await message.answer(
        f"Я определил для тебя такую цель:\n"
        f"Цель: {profile.get('goal', '—')}\n"
        f"Калории: {profile.get('target_cal', '—')} ккал\n"
        f"БЖУ: {profile.get('p_goal', '—')} / {profile.get('f_goal', '—')} / {profile.get('c_goal', '—')}\n\n"
        "Чтобы сохранить цель - нажми кнопку 'ОК', чтобы задать цель вручную - нажми 'Изменить'.",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="ОК"), types.KeyboardButton(text="Изменить")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )

# --- Подтверждение цели ---
@router.message(Registration.confirm_goal)
async def confirm_goal_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    profile = data.get("profile", {})

    if message.text.lower() == "ок":
        add_user_profile(message.from_user.id, profile)
        await message.answer(
            f"✅ Профиль сохранён!\n\n"
            f"Цель: {profile['goal']}\n"
            f"Калорийность: {profile['target_cal']} ккал\n"
            f"БЖУ: {profile['p_goal']} / {profile['f_goal']} / {profile['c_goal']}"
        )
        await state.clear()
        return

    await state.update_data(profile=profile)
    await state.set_state(Registration.set_macros)
    await message.answer(
        "Укажи желаемую калорийность и БЖУ через слеш, например:\n"
        "1900/75/100/250 (ккал/белки/жиры/углеводы)"
    )

# --- Ввод калорий и БЖУ ---
@router.message(Registration.set_macros)
async def set_macros_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    profile = data.get("profile", {})

    try:
        target_cal, p_goal, f_goal, c_goal = map(int, message.text.split("/"))
        profile.update({
            "target_cal": target_cal,
            "p_goal": p_goal,
            "f_goal": f_goal,
            "c_goal": c_goal
        })
    except:
        await message.answer("Неверный формат. Попробуй ещё раз в формате ккал/белки/жиры/углеводы")
        return

    add_user_profile(message.from_user.id, profile)

    await message.answer(
        f"✅ Профиль сохранён!\n\n"
        f"Цель: {profile['goal']}\n"
        f"Калорийность: {profile['target_cal']} ккал\n"
        f"БЖУ: {profile['p_goal']} / {profile['f_goal']} / {profile['c_goal']}"
    )
    await state.clear()
