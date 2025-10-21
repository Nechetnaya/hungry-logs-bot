import csv
from pathlib import Path
from datetime import date

USERS_FILE = Path("data/users.csv")
MEALS_FILE = Path("data/meals.csv")

class CSVClient:
    def __init__(self, users_file="users.csv", meals_file="meals.csv"):
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
        """Считаем суммарное БЖУ и калории за день"""
        if for_date is None:
            for_date = date.today().isoformat()

        total = {"calories": 0, "protein": 0, "fat": 0, "carbs": 0}
        for meal in self.get_meals():
            if int(meal["user_id"]) == user_id and meal["date"] == for_date:
                total["calories"] += float(meal.get("calories", 0))
                total["protein"] += float(meal.get("protein", 0))
                total["fat"] += float(meal.get("fat", 0))
                total["carbs"] += float(meal.get("carbs", 0))
        return total

