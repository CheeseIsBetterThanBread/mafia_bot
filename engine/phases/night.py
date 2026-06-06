from asyncio import create_task, sleep
import random

from config.settings import (
    NIGHT_CALLBACK_TEMPLATE,
    NULL_OPTION,
    THIEF_TIME,
    THIEF_LOWER,
    THIEF_UPPER,
    NIGHT_TIME,
    REMINDER_OFFSET,
    NIGHT_LOWER,
    NIGHT_UPPER,
)

from game_info.role_actions import NightAction, ROLE_NIGHT_ACTIONS

from connection.events import ResponseBase, ResponseWithOptions
from connection.event_bus import EventBus
from connection.queries import QueryType

from utils.logger import LOGGER

from engine.game_state import Game, GameState
from engine.services.night_resolution import resolve_night


async def start_night(bus: EventBus, game: Game):
    game.state = GameState.NIGHT_THIEF
    game.night_actions = {}
    game.expected_night_actors = {}

    for p in game.players.values():
        p.is_glued = False
        p.has_alibi = False

    alive_players = game.get_alive_players()

    thief = next((p for p in alive_players if p.role == "Вор"), None)
    thief_in_preset = "Вор" in game.current_preset

    if not thief_in_preset:
        await start_night_others(bus, game)
        return

    create_task(thief_timeout_logic(bus, game, game.day_count))

    response = ResponseBase(
        game.chat_id,
        f"🌙 Ждем ход Вора (у него есть {THIEF_TIME} секунд)...",
        valid=True,
    )
    await bus.emit(response)

    if not thief:
        await sleep(random.randint(THIEF_LOWER, THIEF_UPPER))

        response = ResponseBase(game.chat_id, "🤐 Вор никого не заклеил.", valid=True)
        await bus.emit(response)

        await start_night_others(bus, game)
        return

    thief_action_info = ROLE_NIGHT_ACTIONS["Вор"][0]
    game.expected_night_actors[thief.user_id] = [thief_action_info[0]]

    generate_callback = lambda number: NIGHT_CALLBACK_TEMPLATE.format(
        chat_id=game.chat_id, action=thief_action_info[0], target=number
    )
    thief_options = [
        (f"№{t.number} ({t.name})", generate_callback(t.number)) for t in alive_players
    ]
    thief_options.append(("Никого не клеить", generate_callback(NULL_OPTION)))

    response = ResponseWithOptions(
        thief_options,
        thief.user_id,
        thief_action_info[1],
        valid=True,
        cmd=QueryType.NIGHT_ACTION,
    )
    try:
        await bus.emit(response)
        return
    except Exception as e:
        LOGGER.error(f"Ошибка отправки Вору: {e}")
        response = ResponseBase(game.chat_id, "🤐 Вор никого не заклеил.", valid=True)
        await bus.emit(response)

        game.expected_night_actors.clear()
        if thief:
            thief.last_rek = None
        await start_night_others(bus, game)


async def start_night_others(bus: EventBus, game: Game):
    game.state = GameState.NIGHT
    game.expected_night_actors.clear()
    alive_players = game.get_alive_players()

    response = ResponseBase(
        game.chat_id,
        f"⏳ Мафия и активные роли делают свой ход. У вас есть {NIGHT_TIME} секунд на все действия!",
        valid=True,
    )
    await bus.emit(response)

    create_task(night_timeout_logic(bus, game, game.day_count))

    for p in alive_players:
        if p.role == "Вор" or p.is_glued:
            continue

        if p.role not in ROLE_NIGHT_ACTIONS.keys():
            continue

        actions = ROLE_NIGHT_ACTIONS[p.role]

        generate_callback = lambda action, number: NIGHT_CALLBACK_TEMPLATE.format(
            chat_id=game.chat_id, action=action.value, target=number
        )
        game.expected_night_actors[p.user_id] = [act[0] for act in actions]
        game.night_actions.setdefault(p.user_id, {})

        for act_code, text in actions:
            action_options = []
            match act_code:
                case NightAction.MANIAC_HEAL:
                    button_text = ROLE_NIGHT_ACTIONS[p.role][1][1]
                    action_options = [
                        (button_text, generate_callback(act_code, p.number))
                    ]
                case NightAction.TWO_FACE_CHECK:
                    if p.found_mafia:
                        continue
                case NightAction.TWO_FACE_KILL:
                    if not p.found_mafia:
                        continue
                case other:
                    action_options = [
                        (f"№{t.number} ({t.name})", generate_callback(other, t.number))
                        for t in alive_players
                    ]

            response = ResponseWithOptions(
                action_options, p.user_id, text, valid=True, cmd=QueryType.NIGHT_ACTION
            )
            await bus.emit(response)

    if not game.expected_night_actors:
        if game.simulation:
            await sleep(random.randint(NIGHT_LOWER, NIGHT_UPPER))
        await resolve_night(bus, game)


async def thief_timeout_logic(bus: EventBus, game: Game, current_day: int):
    await sleep(THIEF_TIME)
    if game.state == GameState.NIGHT_THIEF and game.day_count == current_day:
        response = ResponseBase(game.chat_id, "🤐 Вор никого не заклеил.", valid=True)
        await bus.emit(response)

        game.expected_night_actors.clear()
        thief = next((p for p in game.get_alive_players() if p.role == "Вор"), None)
        if thief:
            thief.last_rek = None
        await start_night_others(bus, game)


async def night_timeout_logic(bus: EventBus, game: Game, current_day: int):
    await sleep(NIGHT_TIME - REMINDER_OFFSET)
    if game.state == GameState.NIGHT and game.day_count == current_day:
        for uid in game.expected_night_actors.keys():
            response = ResponseBase(
                uid,
                f"⏳ <b>Осталось {REMINDER_OFFSET} секунд!</b> Поторопитесь сделать свой выбор, иначе ваш ход сгорит.",
                parse_mode="HTML",
                valid=True,
            )
            await bus.emit(response)

        await sleep(REMINDER_OFFSET)

        if game.state == GameState.NIGHT and game.day_count == current_day:
            response = ResponseBase(
                game.chat_id,
                "⏰ <b>Время вышло!</b> Ночь затянулась.",
                parse_mode="HTML",
                valid=True,
            )
            await bus.emit(response)

            game.expected_night_actors.clear()

            await resolve_night(bus, game)
