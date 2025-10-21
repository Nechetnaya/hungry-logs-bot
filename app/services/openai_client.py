from datetime import datetime

from openai import OpenAI
import json
from app.config import OPENAI_API_KEY


client = OpenAI(api_key=OPENAI_API_KEY)

def get_user_goal(answers_text: str) -> dict:
    prompt = f"""
    Ты — нутрициолог-ассистент. 
    На основе ответов пользователя составь его профиль питания в формате JSON.

    Формат JSON (ключи строго такие):
    {{
      "age": число,
      "sex": "м" или "ж",
      "height": число в см,
      "weight": число в кг,
      "activity": текст коротко (например "сидячая", "умеренная", "высокая"),
      "goal": текст ("похудение", "набор", "поддержание"),
      "target_cal": число — рассчитанная дневная норма калорий по формуле Mifflin–St Jeor,
      "p_goal": число — белки (г),
      "f_goal": число — жиры (г),
      "c_goal": число — углеводы (г)
    }}

    Ответ должен содержать только JSON без комментариев и текста.

    Ответы пользователя:
    {answers_text}
    """

    response = client.chat.completions.create(
        model="gpt-5-nano-2025-08-07",
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # fallback, если что-то пойдет не так
        return {}


async def parse_meal_text(text: str, user_id: int) -> dict:
    """
    Возвращает JSON с keys: protein, fat, carbs, calories, date
    Если не понял, возвращает {"clarification": "уточняющий вопрос"}
    """
    prompt = f"""
    Ты помощник для подсчёта БЖУ. 
    Твоя задача — преобразовать текст о приёме пищи в JSON со следующими полями:
    - protein: количество белков в граммах
    - fat: количество жиров в граммах
    - carbs: количество углеводов в граммах
    - calories: калории

    Постарайся посчитать как можно точнее по тем данным, что у тебя есть. Не задавай дополнительнеы вопросы.

    Текст для анализа: "{text}"
    """

    response = client.chat.completions.create(
        model="gpt-5-nano-2025-08-07",
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.choices[0].message.content.strip()

    try:
        data = eval(content)  # ожидаем dict
    except Exception:
        return {"clarification": "Не понял, можешь описать продукты точнее?"}

    # Добавляем дату
    data.setdefault("date", datetime.today().strftime("%Y-%m-%d"))
    return data

