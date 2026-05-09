import asyncio
import random

from config.settings import NIGHT_CALLBACK_TEMPLATE, NULL_OPTION

from connection.events import ResponseBase, ResponseWithOptions
from connection.event_bus import EventBus

from utils.logger import LOGGER

from engine.game_state import Game, GameState
from engine.services.night_resolution import resolve_night


async def start_night(bus: EventBus, game: Game):
    game.state = GameState.NIGHT_THIEF
    game.night_actions = {}
    game.expected_night_actors = {}

    asyncio.create_task(thief_timeout_logic(bus, game, game.day_count))

    for p in game.players.values():
        p.is_glued = False
        p.has_alibi = False

    alive_players = game.get_alive_players()

    thief = next((p for p in alive_players if p.role == "Вор"), None)
    thief_in_preset = "Вор" in game.current_preset

    if not thief_in_preset:
        await start_night_others(bus, game)
        return

    response = ResponseBase(
        game.chat_id,
        "🌙 Ждем ход Вора (у него есть 1 минута)...",
        valid=True
    )
    await bus.emit(response)

    if not thief:
        await asyncio.sleep(random.randint(20, 45))

        response = ResponseBase(
            game.chat_id,
            "🤐 Вор никого не заклеил.",
            valid=True
        )
        await bus.emit(response)

        await start_night_others(bus, game)
        return


    game.expected_night_actors[thief.user_id] = ["rek"]

    generate_callback = lambda number: NIGHT_CALLBACK_TEMPLATE.format(chat_id=game.chat_id, action="rek", target=number)
    thief_options = [(f"№{t.number} ({t.name})", generate_callback(t.number)) for t in alive_players]
    thief_options.append(("Никого не клеить", generate_callback(NULL_OPTION)))

    response = ResponseWithOptions(
        thief_options,
        thief.user_id,
        "Кого будем клеить?",
        valid=True
    )
    try:
        await bus.emit(response)
        return
    except Exception as e:
        LOGGER.error(f"Ошибка отправки Вору: {e}")
        response = ResponseBase(
            game.chat_id,
            "🤐 Вор никого не заклеил.",
            valid=True
        )
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
        "⏳ Мафия и активные роли делают свой ход. У вас есть ровно 3 минуты на все действия!",
        valid=True
    )
    await bus.emit(response)

    asyncio.create_task(night_timeout_logic(bus, game, game.day_count))

    for p in alive_players:
        if p.role == "Вор" or p.is_glued: continue

        actions = []
        if p.role in game.mafia_team: actions.append(("vote", "Кого убиваем?"))
        if p.role == "Доктор": actions.append(("heal", "Кого будем лечить? (нельзя того же, что и вчера)"))
        if p.role == "Тула": actions.append(("tula", "К кому идем? (хил + алиби)"))
        if p.role == "Шериф": actions.append(("check_s", "Кого проверим на мафию?"))
        if p.role == "Дон": actions.append(("check_d", "Кого проверим на Шерифа?"))
        if p.role == "Адвокат": actions.append(("alibi", "Кому даем алиби на день?"))
        if p.role == "Ниндзя": actions.append(("sur", "В кого кидаем сюрикен?"))
        if p.role == "Маньяк без бинтов": actions.append(("man_k", "Кого убиваем?"))
        if p.role == "Маньяк с бинтами":
            actions.append(("man_k", "Кого убиваем? (ИЛИ выберите лечение себя)"))
            actions.append(("man_h", "Вылечить себя?"))
        if p.role == "Двуликий":
            if getattr(p, 'found_mafia', False):
                actions.append(("dvul_k", "Кого убиваем?"))
            else:
                actions.append(("dvul_j", "Ищем мафию (проверка):"))

        generate_callback = lambda action, number: NIGHT_CALLBACK_TEMPLATE.format(chat_id=game.chat_id, action=action, target=number)
        if actions:
            game.expected_night_actors[p.user_id] = [act[0] for act in actions]
            game.night_actions.setdefault(p.user_id, {})
            for act_code, text in actions:
                action_options = [(f"№{t.number} ({t.name})", generate_callback(act_code, t.number)) for t in alive_players]
                if act_code == "man_h":
                    action_options = [("Лечить себя", generate_callback(act_code, p.number))]

                response = ResponseWithOptions(
                    action_options,
                    p.user_id,
                    text,
                    valid=True
                )
                await bus.emit(response)

    if not game.expected_night_actors:
        await resolve_night(bus, game)


async def thief_timeout_logic(bus: EventBus, game: Game, current_day: int):
    await asyncio.sleep(60)
    if game.state == GameState.NIGHT_THIEF and game.day_count == current_day:
        response = ResponseBase(
            game.chat_id,
            "🤐 Вор никого не заклеил.",
            valid=True
        )
        await bus.emit(response)

        game.expected_night_actors.clear()
        thief = next((p for p in game.get_alive_players() if p.role == "Вор"), None)
        if thief:
            thief.last_rek = None
        await start_night_others(bus, game)


async def night_timeout_logic(bus: EventBus, game: Game, current_day: int):
    await asyncio.sleep(120)
    if game.state == GameState.NIGHT and game.day_count == current_day:
        for uid in game.expected_night_actors.keys():
            response = ResponseBase(
                uid,
                "⏳ <b>Осталась 1 минута!</b> Поторопитесь сделать свой выбор, иначе ваш ход сгорит.",
                parse_mode="HTML",
                valid=True
            )
            await bus.emit(response)

        await asyncio.sleep(60)

        if game.state == GameState.NIGHT and game.day_count == current_day:
            response = ResponseBase(
                game.chat_id,
                "⏰ <b>Время вышло!</b> Ночь затянулась.",
                parse_mode="HTML",
                valid=True
            )
            await bus.emit(response)

            game.expected_night_actors.clear()
            await resolve_night(bus, game)
