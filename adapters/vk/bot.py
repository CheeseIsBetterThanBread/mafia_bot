import asyncio

from vkbottle import Bot

from adapters.vk.adapter import VkAdapter
from adapters.vk.handlers import setup_labeler

from config.settings import VK_BOT_TOKEN

from connection.event_bus import prepare_bus

from engine.core import GameEngine

from utils.validate import validate_adapter


async def main():
    bus = prepare_bus()
    bot = Bot(token=VK_BOT_TOKEN)
    labeler = setup_labeler(bus)
    bot.labeler = labeler

    adapter = VkAdapter(bot, bus)
    validate_adapter(bus, adapter)

    engine = GameEngine(bus)
    engine.register()

    await bot.run_polling()


def run_bot():
    asyncio.run(main())
