from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault

# --- Список всех команд в одном месте ---
COMMANDS = [
    ("statistics", "Статистика за день, неделю, 4 недели"),
    ("goal", "Посмотреть текущую цель"),
    ("update_goal", "Изменить цель"),
    ("delete_last_meal", "Удалить последний приём пищи"),
    ("start", "Регистрация"),
    ("restart", "Удалить профиль и начать заново"),
    ("help", "Список всех команд"),
]


async def set_default_commands(bot: Bot):
    """Устанавливает команды, отображаемые в меню Telegram."""
    await bot.set_my_commands(
        [BotCommand(command=c, description=d) for c, d in COMMANDS],
        scope=BotCommandScopeDefault()
    )

