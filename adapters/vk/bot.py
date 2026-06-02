import asyncio

from vkbottle import Bot
from vkbottle import Keyboard, KeyboardButtonColor, Text

from adapters.vk.adapter import VkAdapter

from config.settings import VK_BOT_TOKEN, VK_GROUP_ID

from connection.event_bus import prepare_bus

from engine.core import GameEngine

from utils.logger import LOGGER
from utils.validate import validate_adapter


def create_commands_keyboard() -> Keyboard:
    keyboard = Keyboard(inline=False)

    keyboard.add(Text("/alive"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("/status"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("/roles"), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()

    keyboard.add(Text("/nominate"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("/vote"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("/balance"), color=KeyboardButtonColor.SECONDARY)
    keyboard.row()

    keyboard.add(Text("/speech"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("/end_speech"), color=KeyboardButtonColor.SECONDARY)
    keyboard.row()

    keyboard.add(Text("/description"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("/nominated"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("/voted"), color=KeyboardButtonColor.SECONDARY)
    keyboard.row()

    keyboard.add(Text("/help"), color=KeyboardButtonColor.SECONDARY)

    return keyboard


async def send_welcome_with_keyboard(bot: Bot, peer_id: int):
    welcome_text = """
🤖 **Бот для игры Мафия** 🤖

Я помогу вам организовать и провести игру в Мафию!

🎮 **Игровые команды:**
• /alive - Показать живых игроков
• /status - Статус игроков
• /roles - Список ролей
• /description - Описание ролей

⚖️ **Ход игры:**
• /nominate - Выставить игрока
• /vote - Проголосовать
• /balance - Голосование при балансе

🎙️ **Речи:**
• /speech - Начать речь
• /end_speech - Завершить речь

💡 **Используйте кнопки ниже для быстрого доступа к командам!**
    """

    keyboard = create_commands_keyboard()

    await bot.api.messages.send(
        peer_id=peer_id, message=welcome_text, random_id=0, keyboard=keyboard.get_json()
    )


async def update_commands_keyboard(bot: Bot, peer_id: int, message_id: int = None):
    keyboard = create_commands_keyboard()

    if message_id:
        await bot.api.messages.edit(
            peer_id=peer_id,
            message_id=message_id,
            message="🔧 **Обновленное меню команд:**",
            keyboard=keyboard.get_json(),
        )
    else:
        await bot.api.messages.send(
            peer_id=peer_id,
            message="🔧 **Меню команд:**",
            random_id=0,
            keyboard=keyboard.get_json(),
        )


async def main():
    bot = Bot(token=VK_BOT_TOKEN)
    bus = prepare_bus()

    adapter = VkAdapter(bot, bus)
    validate_adapter(bus, adapter)

    engine = GameEngine(bus)
    engine.register()

    try:
        community_id = -VK_GROUP_ID
        await send_welcome_with_keyboard(bot, community_id)
    except Exception as e:
        LOGGER.error(f"Не удалось отправить приветственное сообщение: {e}")

    await bot.run_polling()


def run_bot():
    asyncio.run(main())
