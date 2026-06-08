import asyncio
import random

from connection.events import ResponseBase
from connection.event_bus import EventBus

from game_info.role_actions import NightAction

from engine.game_state import Game
from engine.phases.day import start_day
from engine.services.victory import check_victory

from utils.logger import LOGGER


async def generate_random_moves(bus: EventBus, game: Game):
    alive_players = game.get_alive_players()

    for p in alive_players:
        if p.user_id in game.night_actions:
            continue

        if p.is_glued:
            continue

        if p.role == "Ниндзя":
            target = random.choice(alive_players)
            game.night_actions.setdefault(p.user_id, {})[
                NightAction.SHURIKEN
            ] = target.number
            LOGGER.verbose_debug(f"Ninja skipped night move: send to {target.user_id}")

            response = ResponseBase(
                p.user_id,
                f"⚠️ Вы проспали ход! Бот случайно бросил ваш сюрикен в Игрока №{target.number}.",
                valid=True,
            )
            asyncio.create_task(bus.emit(response))
            continue

        if p.role == "Тула":
            LOGGER.verbose_debug("Tula skipped night move")
            valid_targets = [t for t in alive_players if t.number != p.last_healed]
            if valid_targets:
                target = random.choice(valid_targets)
                game.night_actions.setdefault(p.user_id, {})[
                    NightAction.TULA
                ] = target.number

                response = ResponseBase(
                    p.user_id,
                    f"⚠️ Вы проспали ход! Бот случайно отправил вас к Игроку №{target.number}.",
                    valid=True,
                )
                asyncio.create_task(bus.emit(response))
            else:
                p.last_healed = None

            continue

        if p.role in ["Маньяк без бинтов", "Маньяк с бинтами"]:
            if p.role == "Маньяк с бинтами":
                p.last_man_heal = False

            target = random.choice(alive_players)
            game.night_actions.setdefault(p.user_id, {})[
                NightAction.MANIAC_KILL
            ] = target.number
            LOGGER.verbose_debug(f"Maniac skipped night move: send to {target.user_id}")

            response = ResponseBase(
                p.user_id,
                f"⚠️ Вы проспали ход! Бот случайно отправил вас убивать Игрока №{target.number}.",
                valid=True,
            )
            asyncio.create_task(bus.emit(response))
            continue

        if p.role == "Двуликий" and getattr(p, "found_mafia", False):
            target = random.choice(alive_players)
            game.night_actions.setdefault(p.user_id, {})[
                NightAction.TWO_FACE_KILL
            ] = target.number
            LOGGER.verbose_debug(
                f"Two face skipped night move: send to {target.user_id}"
            )

            response = ResponseBase(
                p.user_id,
                f"⚠️ Вы проспали ход! Бот случайно отправил вас убивать Игрока №{target.number}.",
                valid=True,
            )
            asyncio.create_task(bus.emit(response))
            continue

        if p.role == "Доктор":
            LOGGER.verbose_debug("Doctor skipped night move")
            p.last_healed = None

        if p.role == "Адвокат":
            LOGGER.verbose_debug("Lawyer skipped night move")
            p.last_alibi = None


async def resolve_night(bus: EventBus, game: Game):
    await generate_random_moves(bus, game)

    healed = set()
    mafia_votes = {}
    killed_this_night = set()
    putana_client = None

    shurikens_before = {p.number for p in game.get_alive_players() if p.shurikens > 0}
    mafia_dead = not any(
        p.is_alive for p in game.get_alive_players() if p.role in game.mafia_team
    )
    mafia_blocked = (
        any(p.is_glued for p in game.get_alive_players() if p.role in game.mafia_team)
        or mafia_dead
    )

    actions = []
    for uid, acts in game.night_actions.items():
        for code, target in acts.items():
            actions.append(
                {
                    "actor": game.players[uid],
                    "code": code,
                    "target": game.players_by_number[target],
                }
            )

    for a in actions:
        if a["actor"].is_glued:
            continue
        if a["code"] == NightAction.HEAL:
            healed.add(a["target"].number)
            a["actor"].last_healed = a["target"].number
            a["target"].shurikens = 0
        elif a["code"] == NightAction.TULA:
            a["target"].has_alibi = True
            a["actor"].last_healed = a["target"].number
            a["target"].shurikens = 0
            putana_client = a["target"]
        elif a["code"] == NightAction.MANIAC_HEAL:
            healed.add(a["target"].number)
            a["target"].shurikens = 0

    def is_healed(number):
        healed_by_others = number in healed
        if healed_by_others:
            return True

        return putana_client is not None and number == putana_client.number

    for a in actions:
        if a["code"] == NightAction.ALIBI and not a["actor"].is_glued:
            a["target"].has_alibi = True
            a["actor"].last_alibi = a["target"].number

    for a in actions:
        if a["code"] == NightAction.SHURIKEN and not a["actor"].is_glued:
            if not is_healed(a["target"].number):
                a["target"].shurikens += 1

    mafia_victim = None
    if not mafia_blocked:
        for a in actions:
            if a["code"] == NightAction.VOTE and not a["actor"].is_glued:
                weight = 2 if a["actor"].role == "Дон" else 1
                mafia_votes[a["target"].number] = (
                    mafia_votes.get(a["target"].number, 0) + weight
                )
        if mafia_votes:
            max_v = max(mafia_votes.values())
            leaders = [t for t, v in mafia_votes.items() if v == max_v]
            if leaders:
                mafia_victim = game.players_by_number[random.choice(leaders)]
        else:
            LOGGER.verbose_debug("Entire mafia skipped night move")
            alive_players = game.get_alive_players()
            if alive_players and not game.simulation:
                mafia_victim = random.choice(alive_players)

    solo_victims = []
    for a in actions:
        if a["actor"].is_glued:
            continue
        if a["code"] in [NightAction.MANIAC_KILL, NightAction.TWO_FACE_KILL]:
            solo_victims.append(a["target"])

    if mafia_victim:
        if not is_healed(mafia_victim.number) and mafia_victim.role != "Бессмертный":
            killed_this_night.add(mafia_victim.number)

    for victim in solo_victims:
        if not is_healed(victim.number) and victim.role != "Бессмертный":
            killed_this_night.add(victim.number)

    for p in game.get_alive_players():
        if p.shurikens >= 2 and not is_healed(p.number):
            if p.role == "Бессмертный":
                p.shurikens = 0
            else:
                killed_this_night.add(p.number)

    for p in game.get_alive_players():
        if p.role == "Тула" and p.number in killed_this_night:
            if not putana_client or putana_client.number == p.number:
                continue
            if putana_client.role == "Бессмертный" or putana_client.number in healed:
                continue
            killed_this_night.add(putana_client.number)

    announcement = "☀️ Город просыпается.\n\n"
    if killed_this_night:
        for num in killed_this_night:
            game.players_by_number[num].is_alive = False
        announcement += (
            f"💀 Этой ночью были убиты: {', '.join(map(str, killed_this_night))}.\n"
        )
    else:
        announcement += "🕊 Этой ночью никто не умер!\n"

    lost_shurikens = [
        num
        for num in shurikens_before
        if game.players_by_number[num].is_alive
        and game.players_by_number[num].shurikens == 0
    ]
    if lost_shurikens:
        announcement += f"🩹 Сюрикены были успешно извлечены (сброшены) у игроков: {', '.join(map(str, lost_shurikens))}\n"

    current_shurikens = [p.number for p in game.get_alive_players() if p.shurikens == 1]
    if current_shurikens:
        announcement += f"🥷 Внимание! По 1 сюрикену сейчас висит на игроках: {', '.join(map(str, current_shurikens))}\n"

    response = ResponseBase(game.chat_id, announcement, valid=True)
    await bus.emit(response)

    if await check_victory(bus, game):
        return

    await start_day(bus, game)
