from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from adapters.base import fallback_bus

from config.settings import (
    TELEGRAM_ADMINS,
    NOMINATE_CALLBACK_TEMPLATE,
    NOMINATE_TYPES,
    VOTE_CALLBACK_TEMPLATE,
    VOTE_TYPES,
    BALANCE_CALLBACK_TEMPLATE,
    BALANCE_TYPES,
    NIGHT_CALLBACK_TEMPLATE,
    NIGHT_TYPES,
)

from game_info.role_actions import NightAction

from connection.events import (
    StartGameQuery,
    JoinQuery,
    RunQuery,
    TerminateQuery,
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

from game_info.help import HELP_TEXT

from utils.logger import LOGGER
from utils.parser import TemplateParser

router = Router()


def setup_bus(bus: EventBus):
    """
    Пробрасываем bus внутрь handlers
    """
    router.bus = bus
    return router


# --- START / HELP ---


@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.chat.type == "private":
        LOGGER.info(f" {message.from_user.id} - {message.from_user.username} ")
        await message.answer(
            "Привет! Я бот для Мафии.\nДобавь меня в группу и напиши /start_game"
        )
        await message.answer(f"{message.from_user.id}")


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, parse_mode="HTML")


# --- СОЗДАНИЕ ИГРЫ ---


@router.message(Command("start_game"))
async def cmd_start_game(message: Message):
    query = StartGameQuery(
        QueryType.START_GAME,
        TELEGRAM_ADMINS,
        message.chat.id,
        message.from_user.id,
        message.chat.type,
    )
    await getattr(router, "bus", fallback_bus).emit(query)


# --- JOIN (кнопка) ---


@router.callback_query(F.data == "join_game")
async def handle_join_game(callback: CallbackQuery):
    query = JoinQuery(
        QueryType.JOIN_GAME,
        TELEGRAM_ADMINS,
        callback.message.chat.id,
        callback.from_user.id,
        callback,
        callback.from_user.username,
    )
    await getattr(router, "bus", fallback_bus).emit(query)


# --- НАЧАЛО ИГРЫ ---


@router.message(Command("run"))
async def cmd_run(message: Message):
    query = RunQuery(
        QueryType.RUN, TELEGRAM_ADMINS, message.chat.id, message.from_user.id
    )
    await getattr(router, "bus", fallback_bus).emit(query)


# --- ЗАВЕРШЕНИЕ ИГРЫ ---


@router.message(Command("terminate"))
async def cmd_terminate(message: Message):
    query = TerminateQuery(
        QueryType.TERMINATE, TELEGRAM_ADMINS, message.chat.id, message.from_user.id
    )
    await getattr(router, "bus", fallback_bus).emit(query)


# --- ЗАПРОС ИНФОРМАЦИИ ---


@router.message(Command("alive"))
async def cmd_alive(message: Message):
    query = InfoQuery(
        QueryType.ALIVE, TELEGRAM_ADMINS, message.chat.id, message.from_user.id
    )
    await getattr(router, "bus", fallback_bus).emit(query)


@router.message(Command("description"))
async def cmd_description(message: Message):
    query = InfoQuery(
        QueryType.DESCRIPTION, TELEGRAM_ADMINS, message.chat.id, message.from_user.id
    )
    await getattr(router, "bus", fallback_bus).emit(query)


@router.message(Command("roles"))
async def cmd_roles(message: Message):
    query = InfoQuery(
        QueryType.ROLES, TELEGRAM_ADMINS, message.chat.id, message.from_user.id
    )
    await getattr(router, "bus", fallback_bus).emit(query)


@router.message(Command("nominated"))
async def cmd_nominated(message: Message):
    query = InfoQuery(
        QueryType.NOMINATED, TELEGRAM_ADMINS, message.chat.id, message.from_user.id
    )
    await getattr(router, "bus", fallback_bus).emit(query)


@router.message(Command("voted"))
async def cmd_voted(message: Message):
    query = InfoQuery(
        QueryType.VOTED, TELEGRAM_ADMINS, message.chat.id, message.from_user.id
    )
    await getattr(router, "bus", fallback_bus).emit(query)


@router.message(Command("status"))
async def cmd_status(message: Message):
    query = InfoQuery(
        QueryType.STATUS, TELEGRAM_ADMINS, message.chat.id, message.from_user.id
    )
    await getattr(router, "bus", fallback_bus).emit(query)


# --- РЕЧИ ---


@router.message(Command("speech"))
async def cmd_speech(message: Message):
    query = SpeechRelatedQuery(
        QueryType.SPEECH, TELEGRAM_ADMINS, message.chat.id, message.from_user.id
    )
    await getattr(router, "bus", fallback_bus).emit(query)


@router.message(Command("end_speech"))
async def cmd_end_speech(message: Message):
    query = SpeechRelatedQuery(
        QueryType.END_SPEECH, TELEGRAM_ADMINS, message.chat.id, message.from_user.id
    )
    await getattr(router, "bus", fallback_bus).emit(query)


# --- ВЫСТАВЛЕНИЕ ---


@router.message(Command("nominate"))
async def cmd_nominate(message: Message):
    query = PreNominateQuery(
        QueryType.PRE_NOMINATE, TELEGRAM_ADMINS, message.chat.id, message.from_user.id
    )
    await getattr(router, "bus", fallback_bus).emit(query)


@router.callback_query(
    F.data.startswith(NOMINATE_CALLBACK_TEMPLATE.split("|")[0] + "|")
)
async def handle_nominate(callback: CallbackQuery):
    parser = TemplateParser(NOMINATE_CALLBACK_TEMPLATE, NOMINATE_TYPES)
    args = parser.parse(callback.data)
    chat_id, target = args["chat_id"], args["player_number"]

    query = NominateQuery(
        QueryType.NOMINATE,
        TELEGRAM_ADMINS,
        chat_id,
        callback.from_user.id,
        callback,
        target,
    )
    await getattr(router, "bus", fallback_bus).emit(query)


# --- ГОЛОСОВАНИЕ ---


@router.message(Command("vote"))
async def cmd_vote(message: Message):
    query = PreVoteQuery(
        QueryType.PRE_VOTE, TELEGRAM_ADMINS, message.chat.id, message.from_user.id
    )
    await getattr(router, "bus", fallback_bus).emit(query)


@router.callback_query(F.data.startswith(VOTE_CALLBACK_TEMPLATE.split("|")[0] + "|"))
async def handle_vote(callback: CallbackQuery):
    parser = TemplateParser(VOTE_CALLBACK_TEMPLATE, VOTE_TYPES)
    args = parser.parse(callback.data)
    chat_id, target = args["chat_id"], args["player_number"]

    query = VoteQuery(
        QueryType.VOTE,
        TELEGRAM_ADMINS,
        chat_id,
        callback.from_user.id,
        callback,
        target,
    )
    await getattr(router, "bus", fallback_bus).emit(query)


@router.message(Command("balance"))
async def cmd_balance(message: Message):
    query = PreBalanceQuery(
        QueryType.PRE_BALANCE, TELEGRAM_ADMINS, message.chat.id, message.from_user.id
    )
    await getattr(router, "bus", fallback_bus).emit(query)


@router.callback_query(F.data.startswith(BALANCE_CALLBACK_TEMPLATE.split("|")[0] + "|"))
async def handle_balance(callback: CallbackQuery):
    parser = TemplateParser(BALANCE_CALLBACK_TEMPLATE, BALANCE_TYPES)
    args = parser.parse(callback.data)
    chat_id, target = args["chat_id"], args["number"]

    query = BalanceQuery(
        QueryType.BALANCE,
        TELEGRAM_ADMINS,
        chat_id,
        callback.from_user.id,
        callback,
        target,
    )
    await getattr(router, "bus", fallback_bus).emit(query)


# --- ФОРСИРОВАНИЕ НОЧИ ---


@router.message(Command("start_night"))
async def cmd_start_night(message: Message):
    query = StartNightQuery(
        QueryType.START_NIGHT, TELEGRAM_ADMINS, message.chat.id, message.from_user.id
    )
    await getattr(router, "bus", fallback_bus).emit(query)


@router.message(Command("skip_night"))
async def cmd_skip_night(message: Message):
    query = SkipNightQuery(
        QueryType.SKIP_NIGHT, TELEGRAM_ADMINS, message.chat.id, message.from_user.id
    )
    await getattr(router, "bus", fallback_bus).emit(query)


# --- НОЧНЫЕ ДЕЙСТВИЯ ---


@router.callback_query(F.data.startswith(NIGHT_CALLBACK_TEMPLATE.split("|")[0] + "|"))
async def handle_night_action(callback: CallbackQuery):
    parser = TemplateParser(NIGHT_CALLBACK_TEMPLATE, NIGHT_TYPES)
    args = parser.parse(callback.data)
    chat_id, action, target = args["chat_id"], args["action"], args["target"]

    query = NightActionQuery(
        QueryType.NIGHT_ACTION,
        TELEGRAM_ADMINS,
        chat_id,
        callback.from_user.id,
        callback,
        NightAction(action),
        target,
    )
    await getattr(router, "bus", fallback_bus).emit(query)


# --- ЧАТ МАФИИ (ЛС) ---


@router.message(F.chat.type == "private")
async def mafia_chat(message: Message):
    if not message.text:
        return
    if message.text.startswith("/"):
        return

    query = MafiaChatQuery(
        QueryType.MAFIA_CHAT,
        TELEGRAM_ADMINS,
        message.chat.id,
        message.from_user.id,
        str(message.text),
    )
    await getattr(router, "bus", fallback_bus).emit(query)
