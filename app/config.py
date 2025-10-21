import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
SHEET_NAME = os.getenv("SHEET_NAME", "HungryLogs_Data")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")