from datetime import datetime, timedelta
from app.services.csv_client import CSVClient, safe_float

csv_client = CSVClient()

def get_user_target(user_id: int) -> dict:
    """Возвращает текущую цель пользователя в числовых типах."""
    user = csv_client.get_user(user_id)
    if not user:
        return {
            "goal": "не указано",
            "target_cal": 0.0,
            "p_goal": 0.0,
            "f_goal": 0.0,
            "c_goal": 0.0,
        }
    return {
        "goal": user.get("goal", "не указано"),
        "target_cal": safe_float(user.get("target_cal", 0)),
        "p_goal": safe_float(user.get("p_goal", 0)),
        "f_goal": safe_float(user.get("f_goal", 0)),
        "c_goal": safe_float(user.get("c_goal", 0)),
    }

def get_4weeks_stats(user_id: int) -> dict:
    """
    Возвращает структуру:
    {
      "days": [{ "date": date_obj, "calories": float, "protein": float, ... }, ...], # только ненулевые дни за 28 дней
      "avg": { "calories": float, "protein": float, ... }  # среднее по ненулевым дням
    }
    """
    today = datetime.today().date()
    since = today - timedelta(days=28)
    day_totals = []

    for i in range(28):
        day = since + timedelta(days=i)
        day_total = csv_client.get_daily_totals(user_id, day.isoformat())
        # include day only if not all zeros
        if any(safe_float(day_total.get(k, 0)) > 0 for k in ("calories", "protein", "fat", "carbs")):
            day_totals.append({"date": day, **day_total})

    if not day_totals:
        return {"days": [], "avg": {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}}

    n = len(day_totals)
    total_kcal = sum(safe_float(d["calories"]) for d in day_totals)
    total_p = sum(safe_float(d["protein"]) for d in day_totals)
    total_f = sum(safe_float(d["fat"]) for d in day_totals)
    total_c = sum(safe_float(d["carbs"]) for d in day_totals)

    avg = {
        "calories": round(total_kcal / n, 1),
        "protein": round(total_p / n, 1),
        "fat": round(total_f / n, 1),
        "carbs": round(total_c / n, 1),
    }

    return {"days": day_totals, "avg": avg}

def get_4weeks_stats_text(user_id: int) -> str:
    """Удобный текст для prompt / log — использует get_4weeks_stats."""
    stats = get_4weeks_stats(user_id)
    if not stats["days"]:
        return "Нет данных за последние 4 недели."
    a = stats["avg"]
    return f"Средние за 4 недели: {a['calories']} ккал, {a['protein']} г белков, {a['fat']} г жиров, {a['carbs']} г углеводов."
