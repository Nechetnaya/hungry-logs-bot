import gspread
from datetime import date
from google.oauth2.service_account import Credentials
from  app.config import SERVICE_ACCOUNT_FILE, SHEET_NAME

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


class GSheetClient:
    def __init__(self):
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        self.client = gspread.authorize(creds)
        self.users_sheet = self.client.open(SHEET_NAME).worksheet("users")
        self.meals_sheet = self.client.open(SHEET_NAME).worksheet("meals")

    def get_users(self):
        return self.users_sheet.get_all_records()

    def add_user(self, user_data: list):
        self.users_sheet.append_row(user_data)

    def user_exists(self, user_id: int) -> bool:
        users = self.users_sheet.col_values(1)
        return str(user_id) in users

    def add_user_profile(self, user_id: int, profile: dict):
        self.add_user([
            str(user_id),
            profile.get("age", ""),
            profile.get("sex", ""),
            profile.get("height", ""),
            profile.get("weight", ""),
            profile.get("activity", ""),
            profile.get("goal", ""),
            profile.get("target_cal", ""),
            profile.get("p_goal", ""),
            profile.get("f_goal", ""),
            profile.get("c_goal", ""),
        ])

    def get_meals(self):
        return self.meals_sheet.get_all_records()

    def add_meal(self, meal_data: list):
        self.meals_sheet.append_row(meal_data)

    def get_daily_totals(self, user_id: int, for_date: str = None):
        """
        Суммирует калории и БЖУ за указанный день.
        for_date: строка "YYYY-MM-DD", если None — берём сегодня
        """
        if for_date is None:
            for_date = date.today().isoformat()

        meals = self.get_meals()
        total_protein = total_fat = total_carbs = total_calories = 0

        for meal in meals:
            if str(meal["user_id"]) == str(user_id) and meal["date"] == for_date:
                total_protein += float(meal.get("protein", 0))
                total_fat += float(meal.get("fat", 0))
                total_carbs += float(meal.get("carbs", 0))
                total_calories += float(meal.get("calories", 0))

        return {
            "protein": total_protein,
            "fat": total_fat,
            "carbs": total_carbs,
            "calories": total_calories
        }

gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
sheet = gc.open(SHEET_NAME).worksheet("users")
