from aiogram import Bot

from adapters.base import Adapter
from aiogram.client.default import Default
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from connection.events import (
    ResponseBase,
    ResponseWithAlert,
    ResponseWithOptions
)
from connection.event_bus import EventBus


def get_parse_mode(mode: str | None):
    if mode is not None:
        return mode

    return Default("parse_mode")


class TelegramAdapter(Adapter):
    def __init__(self, bot: Bot, bus: EventBus):
        super().__init__()
        self.bot = bot
        self.bus = bus
        self.register()

    def register(self):
        @self.bus.on(ResponseBase)
        async def base_handler(response: ResponseBase):
            await self.bot.send_message(
                response.chat_id,
                response.text,
                parse_mode=get_parse_mode(response.parse_mode)
            )

        @self.bus.on(ResponseWithAlert)
        async def alert_handler(response: ResponseWithAlert):
            if response.is_valid:
                await response.callback.message.edit_text(
                    response.text,
                    reply_markup=response.callback.message.reply_markup,
                    parse_mode=get_parse_mode(response.parse_mode)
                )
                return

            await response.callback.answer(
                response.text,
                show_alert=True,
                parse_mode=get_parse_mode(response.parse_mode)
            )

        @self.bus.on(ResponseWithOptions)
        async def options_handler(response: ResponseWithOptions):
            buttons = []
            for (text, callback_redirect) in response.candidates:
                buttons.append([InlineKeyboardButton(text=text, callback_data=callback_redirect)])

            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await self.bot.send_message(
                response.chat_id,
                response.text,
                reply_markup=keyboard,
                parse_mode=get_parse_mode(response.parse_mode)
            )
