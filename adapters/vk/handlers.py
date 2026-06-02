from vkbottle import Bot, GroupEventType
from vkbottle.bot import BotLabeler, Message, MessageEvent
from vkbottle import Keyboard, KeyboardButtonColor, Callback
from vkbottle.dispatch.rules.base import CommandRule, PayloadRule, FuncRule

from adapters.base import fallback_bus

from config.help import HELP_TEXT
from config.role_actions import NightAction
from config.settings import (
    VK_ADMINS,
    NOMINATE_CALLBACK_TEMPLATE,
    NOMINATE_TYPES,
    VOTE_CALLBACK_TEMPLATE,
    VOTE_TYPES,
    BALANCE_CALLBACK_TEMPLATE,
    BALANCE_TYPES,
    NIGHT_CALLBACK_TEMPLATE,
    NIGHT_TYPES,
)

from connection.events import (
    StartGameQuery,
    JoinQuery,
    RunQuery,
    InfoQuery,
    SpeechRelatedQuery,
    PreNominateQuery,
    NominateQuery,
    PreVoteQuery,
    VoteQuery,
    PreBalanceQuery,
    BalanceQuery,
    StartNightQuery,
    SkipNightQuery,
    NightActionQuery,
    MafiaChatQuery,
)
from connection.event_bus import EventBus
from connection.queries import QueryType

from utils.logger import LOGGER
from utils.parser import TemplateParser
from utils.user_cache import UserNameCache


def setup_bus(bot: Bot, bus: EventBus):
    bot.bus = bus
    return bot


labeler = BotLabeler()
user_name_cache = UserNameCache()


# --- START / HELP ---


@labeler.message(CommandRule("start", ["/"]))
async def cmd_start(message: Message):
    is_private = message.peer_id == message.from_id

    if is_private:
        user_name = await user_name_cache.get_user_name(
            message.ctx_api, message.from_id
        )

        LOGGER.info(f" {message.from_id} - {user_name} ")
        await message.answer(
            "Привет! Я бот для Мафии.\n"
            "Добавь меня в беседу и напишите /start_game\n\n"
            f"Ваш ID: {message.from_id}\n"
            f"Ваше имя: {user_name}"
        )


@labeler.message(CommandRule("help", ["/"]))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, parse_mode="html")


# --- СОЗДАНИЕ ИГРЫ ---


@labeler.message(CommandRule("start_game", ["/"]))
async def cmd_start_game(message: Message):
    query = StartGameQuery(
        QueryType.START_GAME,
        VK_ADMINS,
        message.chat_id or message.peer_id,
        message.from_id,
        "group_chat" if message.chat_id else "private",
    )
    await getattr(message.ctx_api, "bus", fallback_bus).emit(query)


# --- JOIN (кнопка) ---


@labeler.raw_event(
    GroupEventType.MESSAGE_EVENT, MessageEvent, PayloadRule({"type": "join_game"})
)
async def handle_join_game(event: MessageEvent):
    user_name = await user_name_cache.get_user_name(event.ctx_api, event.object.user_id)

    query = JoinQuery(
        QueryType.JOIN_GAME,
        VK_ADMINS,
        event.object.peer_id,
        event.object.user_id,
        event,
        user_name,
    )
    await getattr(event.ctx_api, "bus", fallback_bus).emit(query)


# --- НАЧАЛО ИГРЫ ---


@labeler.message(CommandRule("run", ["/"]))
async def cmd_run(message: Message):
    query = RunQuery(
        QueryType.RUN, VK_ADMINS, message.chat_id or message.peer_id, message.from_id
    )
    await getattr(message.ctx_api, "bus", fallback_bus).emit(query)


# --- ЗАПРОС ИНФОРМАЦИИ ---


@labeler.message(CommandRule("alive", ["/"]))
async def cmd_alive(message: Message):
    query = InfoQuery(
        QueryType.ALIVE, VK_ADMINS, message.chat_id or message.peer_id, message.from_id
    )
    await getattr(message.ctx_api, "bus", fallback_bus).emit(query)


@labeler.message(CommandRule("description", ["/"]))
async def cmd_description(message: Message):
    query = InfoQuery(
        QueryType.DESCRIPTION,
        VK_ADMINS,
        message.chat_id or message.peer_id,
        message.from_id,
    )
    await getattr(message.ctx_api, "bus", fallback_bus).emit(query)


@labeler.message(CommandRule("roles", ["/"]))
async def cmd_roles(message: Message):
    query = InfoQuery(
        QueryType.ROLES, VK_ADMINS, message.chat_id or message.peer_id, message.from_id
    )
    await getattr(message.ctx_api, "bus", fallback_bus).emit(query)


@labeler.message(CommandRule("nominated", ["/"]))
async def cmd_nominated(message: Message):
    query = InfoQuery(
        QueryType.NOMINATED,
        VK_ADMINS,
        message.chat_id or message.peer_id,
        message.from_id,
    )
    await getattr(message.ctx_api, "bus", fallback_bus).emit(query)


@labeler.message(CommandRule("voted", ["/"]))
async def cmd_voted(message: Message):
    query = InfoQuery(
        QueryType.VOTED, VK_ADMINS, message.chat_id or message.peer_id, message.from_id
    )
    await getattr(message.ctx_api, "bus", fallback_bus).emit(query)


@labeler.message(CommandRule("status", ["/"]))
async def cmd_status(message: Message):
    query = InfoQuery(
        QueryType.STATUS, VK_ADMINS, message.chat_id or message.peer_id, message.from_id
    )
    await getattr(message.ctx_api, "bus", fallback_bus).emit(query)


# --- РЕЧИ ---


@labeler.message(CommandRule("speech", ["/"]))
async def cmd_speech(message: Message):
    query = SpeechRelatedQuery(
        QueryType.SPEECH, VK_ADMINS, message.chat_id or message.peer_id, message.from_id
    )
    await getattr(message.ctx_api, "bus", fallback_bus).emit(query)


@labeler.message(CommandRule("end_speech", ["/"]))
async def cmd_end_speech(message: Message):
    query = SpeechRelatedQuery(
        QueryType.END_SPEECH,
        VK_ADMINS,
        message.chat_id or message.peer_id,
        message.from_id,
    )
    await getattr(message.ctx_api, "bus", fallback_bus).emit(query)


# --- ВЫСТАВЛЕНИЕ ---


@labeler.message(CommandRule("nominate", ["/"]))
async def cmd_nominate(message: Message):
    query = PreNominateQuery(
        QueryType.PRE_NOMINATE,
        VK_ADMINS,
        message.chat_id or message.peer_id,
        message.from_id,
    )
    await getattr(message.ctx_api, "bus", fallback_bus).emit(query)


@labeler.raw_event(
    GroupEventType.MESSAGE_EVENT, MessageEvent, PayloadRule({"type": "nominate"})
)
async def handle_nominate(event: MessageEvent):
    parser = TemplateParser(NOMINATE_CALLBACK_TEMPLATE, NOMINATE_TYPES)
    args = parser.parse(event.object.payload.get("data", ""))
    chat_id = args.get("chat_id", event.object.peer_id)
    target = args["player_number"]

    query = NominateQuery(
        QueryType.NOMINATE,
        VK_ADMINS,
        chat_id,
        event.object.user_id,
        event,
        target,
    )
    await getattr(event.ctx_api, "bus", fallback_bus).emit(query)


# --- ГОЛОСОВАНИЕ ---


@labeler.message(CommandRule("vote", ["/"]))
async def cmd_vote(message: Message):
    query = PreVoteQuery(
        QueryType.PRE_VOTE,
        VK_ADMINS,
        message.chat_id or message.peer_id,
        message.from_id,
    )
    await getattr(message.ctx_api, "bus", fallback_bus).emit(query)


@labeler.raw_event(
    GroupEventType.MESSAGE_EVENT, MessageEvent, PayloadRule({"type": "vote"})
)
async def handle_vote(event: MessageEvent):
    parser = TemplateParser(VOTE_CALLBACK_TEMPLATE, VOTE_TYPES)
    args = parser.parse(event.object.payload.get("data", ""))
    chat_id = args.get("chat_id", event.object.peer_id)
    target = args["player_number"]

    query = VoteQuery(
        QueryType.VOTE,
        VK_ADMINS,
        chat_id,
        event.object.user_id,
        event,
        target,
    )
    await getattr(event.ctx_api, "bus", fallback_bus).emit(query)


@labeler.message(CommandRule("balance", ["/"]))
async def cmd_balance(message: Message):
    query = PreBalanceQuery(
        QueryType.PRE_BALANCE,
        VK_ADMINS,
        message.chat_id or message.peer_id,
        message.from_id,
    )
    await getattr(message.ctx_api, "bus", fallback_bus).emit(query)


@labeler.raw_event(
    GroupEventType.MESSAGE_EVENT, MessageEvent, PayloadRule({"type": "balance"})
)
async def handle_balance(event: MessageEvent):
    parser = TemplateParser(BALANCE_CALLBACK_TEMPLATE, BALANCE_TYPES)
    args = parser.parse(event.object.payload.get("data", ""))
    chat_id = args.get("chat_id", event.object.peer_id)
    target = args["number"]

    query = BalanceQuery(
        QueryType.BALANCE,
        VK_ADMINS,
        chat_id,
        event.object.user_id,
        event,
        target,
    )
    await getattr(event.ctx_api, "bus", fallback_bus).emit(query)


# --- ФОРСИРОВАНИЕ НОЧИ ---


@labeler.message(CommandRule("start_night", ["/"]))
async def cmd_start_night(message: Message):
    query = StartNightQuery(
        QueryType.START_NIGHT,
        VK_ADMINS,
        message.chat_id or message.peer_id,
        message.from_id,
    )
    await getattr(message.ctx_api, "bus", fallback_bus).emit(query)


@labeler.message(CommandRule("skip_night", ["/"]))
async def cmd_skip_night(message: Message):
    query = SkipNightQuery(
        QueryType.SKIP_NIGHT,
        VK_ADMINS,
        message.chat_id or message.peer_id,
        message.from_id,
    )
    await getattr(message.ctx_api, "bus", fallback_bus).emit(query)


# --- НОЧНЫЕ ДЕЙСТВИЯ ---


@labeler.raw_event(
    GroupEventType.MESSAGE_EVENT, MessageEvent, PayloadRule({"type": "night_action"})
)
async def handle_night_action(event: MessageEvent):
    parser = TemplateParser(NIGHT_CALLBACK_TEMPLATE, NIGHT_TYPES)
    args = parser.parse(event.object.payload.get("data", ""))
    chat_id = args.get("chat_id", event.object.peer_id)
    action = args["action"]
    target = args["target"]

    query = NightActionQuery(
        QueryType.NIGHT_ACTION,
        VK_ADMINS,
        chat_id,
        event.object.user_id,
        event,
        NightAction(action),
        target,
    )
    await getattr(event.ctx_api, "bus", fallback_bus).emit(query)


# --- ЧАТ МАФИИ (ЛС) ---


@labeler.message(FuncRule(lambda message: message.peer_id == message.from_id))
async def mafia_chat(message: Message):
    if not message.text:
        return
    if message.text.startswith("/"):
        return

    query = MafiaChatQuery(
        QueryType.MAFIA_CHAT,
        VK_ADMINS,
        message.peer_id,
        message.from_id,
        str(message.text),
    )
    await getattr(message.ctx_api, "bus", fallback_bus).emit(query)


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ СОЗДАНИЯ КЛАВИАТУР ---


def create_nominate_keyboard(chat_id: int, players: list) -> Keyboard:
    keyboard = Keyboard(inline=True)

    for i, player in enumerate(players, 1):
        keyboard.add(
            Callback(
                label=f"Игрок {i}: {player['name']}",
                payload={
                    "type": "nominate",
                    "data": f"nominate|chat_id={chat_id}|player_number={i}",
                },
            ),
            color=KeyboardButtonColor.PRIMARY,
        )
        if i % 2 == 0:
            keyboard.row()

    return keyboard


def create_vote_keyboard(chat_id: int, nominated_players: list) -> Keyboard:
    """Создание клавиатуры для голосования"""
    keyboard = Keyboard(inline=True)

    for player in nominated_players:
        keyboard.add(
            Callback(
                label=f"Голосовать за {player['name']}",
                payload={
                    "type": "vote",
                    "data": f"vote|chat_id={chat_id}|player_number={player['id']}",
                },
            ),
            color=KeyboardButtonColor.PRIMARY,
        )
        keyboard.row()

    return keyboard


def create_night_keyboard(chat_id: int, actions: list, targets: list) -> Keyboard:
    """Создание клавиатуры для ночных действий"""
    keyboard = Keyboard(inline=True)

    for action in actions:
        for target in targets:
            keyboard.add(
                Callback(
                    label=f"{action.name} → {target['name']}",
                    payload={
                        "type": "night_action",
                        "data": f"night|chat_id={chat_id}|action={action.value}|target={target['id']}",
                    },
                ),
                color=KeyboardButtonColor.SECONDARY,
            )
            keyboard.row()

    return keyboard


# --- ФАЙЛ ДЛЯ ЗАПУСКА БОТА (main.py) ---
"""
from vkbottle import Bot
from handlers import labeler, setup_bus
from connection.event_bus import EventBus

TOKEN = "YOUR_VK_GROUP_TOKEN"

bot = Bot(token=TOKEN)
bot.labeler = labeler

event_bus = EventBus()  # Ваша реализация EventBus
bot = setup_bus(bot, event_bus)

if __name__ == "__main__":
    bot.run_forever()
"""
