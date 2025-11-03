from aiogram import Router, types
from aiogram.filters import Command
from app.services.commands import COMMANDS

router = Router()

@router.message(Command("help"))
async def show_all_commands(message: types.Message):
    """Отправляет пользователю список всех доступных команд с описанием."""
    lines = ["📋 <b>Список доступных команд:</b>\n"]
    for command, description in COMMANDS:
        lines.append(f"/{command} — {description}")
    text = "\n\n".join(lines)
    await message.answer(text, parse_mode="HTML")
