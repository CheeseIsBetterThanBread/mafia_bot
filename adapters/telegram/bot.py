import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from config.settings import TELEGRAM_BOT_TOKEN
from connection.event_bus import prepare_bus
from engine.core import GameEngine
from utils.validate import validate_adapter

from adapters.telegram.handlers import setup_bus
from adapters.telegram.adapter import TelegramAdapter


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="alive", description="Показать живых игроков"),
        BotCommand(
            command="status", description="Вывести живых игроков и число сюрикенов"
        ),
        BotCommand(command="roles", description="Список ролей в игре"),
        BotCommand(command="description", description="Полное описание ролей"),
        BotCommand(command="nominated", description="Кого уже выставили"),
        BotCommand(command="voted", description="Кто за кого проголосовал"),
        BotCommand(command="speech", description="Начать свою речь"),
        BotCommand(command="end_speech", description="Завершить речь досрочно"),
        BotCommand(command="nominate", description="Выставить на голосование"),
        BotCommand(command="vote", description="Проголосовать на суде"),
        BotCommand(command="balance", description="Голосовать при балансе"),
        BotCommand(command="help", description="Справка по боту"),
    ]

    await bot.set_my_commands(commands)


async def run():
    bot = Bot(TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    bus = prepare_bus()

    adapter = TelegramAdapter(bot, bus)
    adapter.register()
    validate_adapter(bus, adapter)

    engine = GameEngine(bus)
    engine.register()

    router = setup_bus(bus)
    dp.include_router(router)

    await set_commands(bot)
    await dp.start_polling(bot)


def run_bot():
    asyncio.run(run())
