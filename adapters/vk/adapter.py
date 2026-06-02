from typing import Optional

from vkbottle import Bot, Keyboard, KeyboardButtonColor, Callback

from adapters.base import Adapter

from connection.events import ResponseBase, ResponseWithAlert, ResponseWithOptions
from connection.event_bus import EventBus

from connection.queries import QueryType


def format_text(text: str, parse_mode: str | None = None) -> str:
    if parse_mode == "MarkdownV2":
        import re

        text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
        text = re.sub(r"__(.*?)__", r"<u>\1</u>", text)
        text = re.sub(r"~~(.*?)~~", r"<s>\1</s>", text)
        text = re.sub(r"`(.*?)`", r"<code>\1</code>", text)
        text = re.sub(r"\[(.*?)]\((.*?)\)", r'<a href="\2">\1</a>', text)
        return text

    return text


def create_inline_keyboard(candidates: list, cmd: QueryType) -> Optional[Keyboard]:
    if not candidates:
        return None

    cmd_type = ""
    match cmd:
        case QueryType.START_GAME:
            cmd_type = "join_game"
        case QueryType.PRE_NOMINATE:
            cmd_type = "nominate"
        case QueryType.PRE_VOTE:
            cmd_type = "vote"
        case QueryType.PRE_BALANCE:
            cmd_type = "balance"
        case QueryType.NIGHT_ACTION:
            cmd_type = "night_action"
        case _:
            return None

    keyboard = Keyboard(inline=True)

    for text, callback_redirect in candidates:
        keyboard.add(
            Callback(label=text, payload={"type": cmd_type, "data": callback_redirect}),
            color=KeyboardButtonColor.PRIMARY,
        )
        keyboard.row()

    return keyboard


class VkAdapter(Adapter):
    def __init__(self, bot: Bot, bus: EventBus):
        super().__init__()
        self.bot = bot
        self.bus = bus
        self.register()

    def register(self):
        @self.bus.on(ResponseBase)
        async def base_handler(response: ResponseBase):
            if type(response) is not ResponseBase:
                return

            await self.bot.api.messages.send(
                peer_id=response.chat_id,
                message=format_text(response.text, response.parse_mode),
                random_id=0,
            )

        @self.bus.on(ResponseWithAlert)
        async def alert_handler(response: ResponseWithAlert):
            if type(response) is not ResponseWithAlert:
                return

            if response.is_valid:
                await self.bot.api.messages.edit(
                    peer_id=response.callback.peer_id,
                    message_id=response.callback.conversation_message_id,
                    message=format_text(response.text, response.parse_mode),
                    random_id=0,
                )
                return

            await response.callback.show_snackbar(response.text)

        @self.bus.on(ResponseWithOptions)
        async def options_handler(response: ResponseWithOptions):
            if type(response) is not ResponseWithOptions:
                return

            keyboard = create_inline_keyboard(response.candidates, response.cmd)

            await self.bot.api.messages.send(
                peer_id=response.chat_id,
                message=format_text(response.text, response.parse_mode),
                random_id=0,
                keyboard=keyboard.get_json() if keyboard else None,
            )
