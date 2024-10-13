import asyncio

from aiogram import Dispatcher
from aiogram.types import BotCommand

from internal import bot
from routers import router as main_router


dp = Dispatcher()
dp.include_routers(main_router)

commands = [
    BotCommand(command = 'info', description = "Learn about given role"),
    BotCommand(command = 'help', description = "Get help"),
    BotCommand(command = 'start', description = "Enter a game"),
    BotCommand(command = "list", description = "See all current players"),

    BotCommand(command = "put_up", description = "Put someone up for a vote"),
    BotCommand(command = "vote", description = "Vote for person"),
    BotCommand(command = "display", description = "See players that can be voted for"),

    BotCommand(command = "kill", description = "Mafia's/Maniac's night action"),
    BotCommand(command = "heal", description = "Doctor's/Maniac's night action"),
    BotCommand(command = "check", description = "Sheriff's/Don's night action"),
    BotCommand(command = "visit", description = "Tula's night action"),
    BotCommand(command = "mute", description = "Thief's night action"),

    BotCommand(command = 'leave', description = "Leave a game")
]


async def main() -> None:
    await bot.set_my_commands(commands)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
