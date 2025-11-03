import csv
from pathlib import Path
from datetime import date

USERS_FILE = Path("data/users.csv")
MEALS_FILE = Path("data/meals.csv")

def safe_float(value, default=0.0):
    """Преобразует значение в float, пустые/некорректные значения -> default."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return float(default)

class CSVClient:
    def __init__(self, users_file=USERS_FILE, meals_file=MEALS_FILE):
        self.users_file = users_file
        self.meals_file = meals_file
        # создаём файлы, если их нет
        import os, csv
        if not os.path.exists(users_file):
            with open(users_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["user_id","age","sex","height","weight","activity","goal","target_cal","p_goal","f_goal","c_goal"])
        if not os.path.exists(meals_file):
            with open(meals_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["user_id","date","meal_text","protein","fat","carbs","calories"])

    def get_users(self):
        import csv
        with open(self.users_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def user_exists(self, user_id):
        users = self.get_users()
        return any(int(u["user_id"]) == user_id for u in users)

    def add_user(self, user_data):
        import csv
        with open(self.users_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(user_data)

    def get_user(self, user_id):
        users = self.get_users()
        for u in users:
            if int(u["user_id"]) == user_id:
                return u
        return None

    def get_meals(self):
        with open(self.meals_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def add_meal(self, meal_data):
        with open(self.meals_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(meal_data)

    def get_daily_totals(self, user_id, for_date=None):
        """Считаем суммарное БЖУ и калории за день (возвращаем числа float)."""
        if for_date is None:
            for_date = date.today().isoformat()

        total = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
        for meal in self.get_meals():
            try:
                if int(meal["user_id"]) == int(user_id) and meal["date"] == for_date:
                    total["calories"] += safe_float(meal.get("calories", 0))
                    total["protein"] += safe_float(meal.get("protein", 0))
                    total["fat"] += safe_float(meal.get("fat", 0))
                    total["carbs"] += safe_float(meal.get("carbs", 0))
            except (KeyError, ValueError, TypeError):
                # если запись повреждена — пропускаем её
                continue
        return total

    def update_user_target(self, user_id: int, new_goal: dict):
        """Обновляет цель пользователя (new_goal — dict с ключами goal/target_cal/p_goal/f_goal/c_goal)."""
        users = self.get_users()
        for u in users:
            try:
                if int(u["user_id"]) == int(user_id):
                    u["goal"] = str(new_goal.get("goal", u.get("goal", "")))
                    u["target_cal"] = str(new_goal.get("target_cal", u.get("target_cal", "")))
                    u["p_goal"] = str(new_goal.get("p_goal", u.get("p_goal", "")))
                    u["f_goal"] = str(new_goal.get("f_goal", u.get("f_goal", "")))
                    u["c_goal"] = str(new_goal.get("c_goal", u.get("c_goal", "")))
                    break
            except (ValueError, TypeError):
                continue
        self.save_users(users)

    def save_users(self, users):
        with open(self.users_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["user_id", "age", "sex", "height", "weight", "activity", "goal",
                                                   "target_cal", "p_goal", "f_goal", "c_goal"])
            writer.writeheader()
            writer.writerows(users)

    def save_meals(self, meals: list[dict]):
        """Перезаписываем файл meals.csv списком словарей (требует те же поля, что и заголовок)."""
        import csv
        fieldnames = ["user_id", "date", "meal_text", "protein", "fat", "carbs", "calories"]
        with open(self.meals_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(meals)

    def get_all_user_ids(self):
        with open("data/users.csv", "r", encoding="utf-8") as f:
            lines = f.readlines()[1:]  # пропускаем заголовок
        return [int(line.split(",")[0]) for line in lines if line.strip()]
