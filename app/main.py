import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import TELEGRAM_TOKEN_TEST, TELEGRAM_TOKEN
from app.handlers import registration, meals, statistics, meals_delete, help, restart
from app.services.commands import set_default_commands


# --- Инициализация ---
# bot = Bot(token=TELEGRAM_TOKEN_TEST)
bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# --- Подключаем роутеры ---
dp.include_router(registration.router)
dp.include_router(meals.router)
dp.include_router(statistics.router)
dp.include_router(meals_delete.router)
dp.include_router(help.router)
dp.include_router(restart.router)


# --- Точка входа ---
async def main():
    print("🤖 Bot started.")

    # 👇 устанавливаем меню команд в Telegram
    await set_default_commands(bot)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
