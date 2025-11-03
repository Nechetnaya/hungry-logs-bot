from aiogram import Router, F, types
from datetime import date, timedelta

from aiogram.types import ReplyKeyboardRemove

from app.services.csv_client import CSVClient
from app.services.user_data import get_4weeks_stats
from app.services.logger import log_event

router = Router()
csv_client = CSVClient()

# --- Helpers ---
def safe_int(value, default=0):
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return int(default)

def has_nonzero_values(d, keys):
    return any(safe_int(d.get(k, 0)) > 0 for k in keys)

def format_day_stats(user, day_total, day_date=None):
    date_str = day_date.strftime('%d.%m') if day_date else ""
    return (
        f"{date_str}:\n"
        f"Калории: {safe_int(day_total['calories'])} / {user.get('target_cal')}\n"
        f"БЖУ: {safe_int(day_total['protein'])}/{safe_int(day_total['fat'])}/{safe_int(day_total['carbs'])}\n"
    )

# --- /stats menu ---
@router.message(F.text == "/statistics")
async def stats_menu(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="За день"),
             types.KeyboardButton(text="За неделю"),
             types.KeyboardButton(text="За 4 недели")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Выбери период статистики:", reply_markup=keyboard)

# --- show stats ---
@router.message(F.text.in_({"За день", "За неделю", "За 4 недели"}))
async def show_stats(message: types.Message):
    user_id = message.from_user.id
    user = csv_client.get_user(user_id)
    if not user:
        await message.answer("Сначала нужно зарегистрироваться. Напиши /start", reply_markup=ReplyKeyboardRemove())
        return

    await message.answer("⏳ Загружаю статистику...", reply_markup=ReplyKeyboardRemove())

    today = date.today()
    period = message.text
    meals = [m for m in csv_client.get_meals() if int(m.get("user_id", 0)) == user_id]

    if period == "За день":
        day_total = csv_client.get_daily_totals(user_id, today.isoformat())
        if not has_nonzero_values(day_total, ["calories", "protein", "fat", "carbs"]):
            await message.answer("⚠️ Нет событий за сегодня.")
            return

        text = f"📅 Приёмы пищи за сегодня:\n"
        for m in meals:
            if m.get("date") == today.isoformat():
                text += f"- {m.get('meal_text','—')}: {safe_int(m.get('calories'))} ккал, " \
                        f"{safe_int(m.get('protein'))}/{safe_int(m.get('fat'))}/{safe_int(m.get('carbs'))} БЖУ\n"

        text += (
            f"\n📊 Итого за день:\n"
            f"Калории: {safe_int(day_total['calories'])} / {user.get('target_cal')}\n"
            f"Белки: {safe_int(day_total['protein'])} / {user.get('p_goal')}\n"
            f"Жиры: {safe_int(day_total['fat'])} / {user.get('f_goal')}\n"
            f"Углеводы: {safe_int(day_total['carbs'])} / {user.get('c_goal')}"
        )
        await message.answer(text, reply_markup=ReplyKeyboardRemove())
        return

    # --- Статистика за неделю ---
    if period == "За неделю":
        text = "📅 Последние 7 дней:\n"
        totals_list = []

        for i in range(1, 8):  # вчера и 6 предыдущих дней
            day = today - timedelta(days=i)
            day_total = csv_client.get_daily_totals(user_id, day.isoformat())
            totals_list.append(day_total)
            text += format_day_stats(user, day_total, day)

        # Среднее за неделю (исключаем нулевые дни)
        nonzero_days = [d for d in totals_list if has_nonzero_values(d, ["calories", "protein", "fat", "carbs"])]
        if nonzero_days:
            avg = {k: sum(float(d[k]) for d in nonzero_days) / len(nonzero_days)
                   for k in ["calories", "protein", "fat", "carbs"]}
            text += (
                f"\n📊 Среднее за неделю:\n"
                f"Калории: {int(avg['calories'])} / {user['target_cal']}\n"
                f"Белки: {int(avg['protein'])} / {user['p_goal']}\n"
                f"Жиры: {int(avg['fat'])} / {user['f_goal']}\n"
                f"Углеводы: {int(avg['carbs'])} / {user['c_goal']}"
            )
        else:
            text += "\n⚠️ Нет событий за последнюю неделю для расчета среднего."

        await message.answer(text, reply_markup=ReplyKeyboardRemove())
        return

    if period == "За 4 недели":
        stats = get_4weeks_stats(user_id)
        if not stats["days"]:
            await message.answer("⚠️ Нет событий за последние 4 недели.")
            return

        weeks = []
        # соберём по неделям, но используем get_daily_totals (агрегация внутри CSVClient)
        today = date.today()
        week_ranges = []
        for w in range(4):
            end_day = today - timedelta(days=w*7)
            start_day = end_day - timedelta(days=6)
            week_ranges.append((start_day, end_day))

            week_totals = {"calories": 0, "protein": 0, "fat": 0, "carbs": 0}
            days_count = 0
            for i in range(7):
                day = start_day + timedelta(days=i)
                day_total = csv_client.get_daily_totals(user_id, day.isoformat())
                if has_nonzero_values(day_total, ["calories", "protein", "fat", "carbs"]):
                    for k in week_totals:
                        week_totals[k] += safe_int(day_total[k])
                    days_count += 1
            if days_count > 0:
                for k in week_totals:
                    week_totals[k] = int(week_totals[k] / days_count)
            weeks.append(week_totals)

        valid_weeks = [w for w in weeks if has_nonzero_values(w, ["calories","protein","fat","carbs"])]
        if not valid_weeks:
            await message.answer("⚠️ Нет событий за последние 4 недели.", reply_markup=ReplyKeyboardRemove())
            return

        avg_4w = {k: int(sum(w[k] for w in valid_weeks)/len(valid_weeks)) for k in valid_weeks[0]}

        # Вывод по неделям (от старшей к младшей)
        text = "📅 Среднее потребление за 4 недели:\n\n"
        for week, (start_day, end_day) in zip(reversed(weeks), reversed(week_ranges)):
            if has_nonzero_values(week, ["calories","protein","fat","carbs"]):
                text += (
                    f"{start_day.strftime('%d.%m')} — {end_day.strftime('%d.%m')}:\n"
                    f"Калории: {safe_int(week['calories'])} / {user.get('target_cal')}\n"
                    f"БЖУ: {safe_int(week['protein'])}/{safe_int(week['fat'])}/{safe_int(week['carbs'])}\n\n"
                )

        text += (
            f"📊 Среднее за 4 недели:\n"
            f"Калории: {avg_4w['calories']} / {user.get('target_cal')}\n"
            f"Белки: {avg_4w['protein']} / {user.get('p_goal')}\n"
            f"Жиры: {avg_4w['fat']} / {user.get('f_goal')}\n"
            f"Углеводы: {avg_4w['carbs']} / {user.get('c_goal')}"
        )
        await message.answer(text, reply_markup=ReplyKeyboardRemove())
        return

# --- /goal ---
@router.message(F.text == "/goal")
async def show_current_goal(message: types.Message):
    user_id = message.from_user.id
    user = csv_client.get_user(user_id)

    if not user:
        await message.answer("Сначала нужно зарегистрироваться. Напиши /start")
        return

    await message.answer(
        f"🎯 Текущая цель:\n"
        f"Цель: {user.get('goal', '—')}\n"
        f"Калории: {user.get('target_cal', '—')} ккал\n"
        f"БЖУ: {user.get('p_goal', '—')} / {user.get('f_goal', '—')} / {user.get('c_goal', '—')}\n\n"
        f"Для изменения цели отправьте команду /update_goal"
    )
    log_event("goal_viewed", user_id, extra_info=str(user))
