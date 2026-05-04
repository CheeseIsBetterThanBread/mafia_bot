import asyncio
import random

from connection.events import ResponseBase
from connection.event_bus import EventBus

from engine.game_state import Game


async def generate_random_moves(bus: EventBus, game: Game):
    alive_players = game.get_alive_players()

    for p in alive_players:
        if p.user_id in game.night_actions:
            continue

        if p.is_glued:
            continue  # Заклеенные просто спят законно

        if p.role == "Ниндзя":
            target = random.choice(alive_players)
            game.night_actions.setdefault(p.user_id, {})["sur"] = target.number

            response = ResponseBase(
                p.user_id,
                f"⚠️ Вы проспали ход! Бот случайно бросил ваш сюрикен в Игрока №{target.number}."
            )
            asyncio.create_task(bus.emit(response))
            continue

        if p.role == "Тула":
            valid_targets = [t for t in alive_players if t.number != p.last_healed]
            if valid_targets:
                target = random.choice(valid_targets)
                game.night_actions.setdefault(p.user_id, {})["tula"] = target.number

                response = ResponseBase(
                    p.user_id,
                    f"⚠️ Вы проспали ход! Бот случайно отправил вас к Игроку №{target.number}."
                )
                asyncio.create_task(bus.emit(response))
            else:
                p.last_healed = None

            continue

        if p.role in ["Маньяк без бинтов", "Маньяк с бинтами"]:
            if p.role == "Маньяк с бинтами":
                p.last_man_heal = False

            target = random.choice(alive_players)
            game.night_actions.setdefault(p.user_id, {})["man_k"] = target.number

            response = ResponseBase(
                p.user_id,
                f"⚠️ Вы проспали ход! Бот случайно отправил вас убивать Игрока №{target.number}."
            )
            asyncio.create_task(bus.emit(response))
            continue

        if p.role == "Двуликий" and getattr(p, 'found_mafia', False):
            target = random.choice(alive_players)
            game.night_actions.setdefault(p.user_id, {})["dvul_k"] = target.number

            response = ResponseBase(
                p.user_id,
                f"⚠️ Вы проспали ход! Бот случайно отправил вас убивать Игрока №{target.number}."
            )
            asyncio.create_task(bus.emit(response))
            continue

        if p.role == "Доктор":
            p.last_healed = None

        if p.role == "Адвокат":
            p.last_alibi = None


async def resolve_night(bus: EventBus, game: Game):
    await generate_random_moves(bus, game)

    healed = set()
    mafia_votes = {}
    killed_this_night = set()
    putana_client = None

    shurikens_before = {p.number for p in game.get_alive_players() if p.surikens > 0}
    mafia_blocked = any(p.is_glued for p in game.get_alive_players() if p.role in game.mafia_team)

    actions = []
    for uid, acts in game.night_actions.items():
        for code, target in acts.items():
            actions.append({"actor": game.players[uid], "code": code, "target": game.players_by_number[target]})

    for a in actions:
        if a["actor"].is_glued:
            continue
        if a["code"] == "heal":
            healed.add(a["target"].number)
            a["actor"].last_healed = a["target"].number
            a["target"].surikens = 0
        elif a["code"] == "tula":
            healed.add(a["target"].number)
            a["target"].has_alibi = True
            a["actor"].last_healed = a["target"].number
            a["target"].surikens = 0
            putana_client = a["target"]
        elif a["code"] == "man_h":
            healed.add(a["target"].number)

    for a in actions:
        if a["code"] == "alibi" and not a["actor"].is_glued:
            a["target"].has_alibi = True
            a["actor"].last_alibi = a["target"].number

    shurikened_this_night = []

    for a in actions:
        if a["code"] == "sur" and not a["actor"].is_glued:
            if a["target"].number not in healed:
                a["target"].surikens += 1
                shurikened_this_night.append(a["target"].number)

    mafia_victim = None
    if not mafia_blocked:
        for a in actions:
            if a["code"] == "vote" and not a["actor"].is_glued:
                weight = 2 if a["actor"].role == "Дон" else 1
                mafia_votes[a["target"].number] = mafia_votes.get(a["target"].number, 0) + weight
        if mafia_votes:
            max_v = max(mafia_votes.values())
            leaders = [t for t, v in mafia_votes.items() if v == max_v]
            if leaders:
                mafia_victim = game.players_by_number[random.choice(leaders)]
        else:
            # --- ВСЯ МАФИЯ ПРОСПАЛА - СЛУЧАЙНЫЙ ВЫСТРЕЛ ---
            alive_players = game.get_alive_players()
            if alive_players:
                mafia_victim = random.choice(alive_players)

    solo_victims = []
    for a in actions:
        if a["actor"].is_glued:
            continue
        if a["code"] in ["man_k", "dvul_k"]:
            solo_victims.append(a["target"])

    if mafia_victim:
        if mafia_victim.number not in healed and mafia_victim.role != "Бессмертный":
            killed_this_night.add(mafia_victim.number)

    for victim in solo_victims:
        if victim.number not in healed and victim.role != "Бессмертный":
            killed_this_night.add(victim.number)

    for p in game.get_alive_players():
        if p.surikens >= 2 and p.number not in healed:
            if p.role == "Бессмертный":
                p.surikens = 0
            else:
                killed_this_night.add(p.number)

    for p in game.get_alive_players():
        if p.role == "Тула" and p.number in killed_this_night:
            if putana_client and putana_client.number != p.number:
                if putana_client.role != "Бессмертный":
                    killed_this_night.add(putana_client.number)

    announcement = "☀️ Город просыпается.\n\n"
    if killed_this_night:
        for num in killed_this_night: game.players_by_number[num].is_alive = False
        announcement += f"💀 Этой ночью были убиты: {', '.join(map(str, killed_this_night))}.\n"
    else:
        announcement += "🕊 Этой ночью никто не умер!\n"

    lost_shurikens = [num for num in shurikens_before if
                      game.players_by_number[num].is_alive and game.players_by_number[num].surikens == 0]
    if lost_shurikens:
        announcement += f"🩹 Сюрикены были успешно извлечены (сброшены) у игроков: {', '.join(map(str, lost_shurikens))}\n"

    current_shurikens = [p.number for p in game.get_alive_players() if p.surikens == 1]
    if current_shurikens:
        announcement += f"🥷 Внимание! По 1 сюрикену сейчас висит на игроках: {', '.join(map(str, current_shurikens))}\n"

    response = ResponseBase(
        game.chat_id,
        announcement
    )
    await bus.emit(response)

    from engine.victory import check_victory
    if await check_victory(bus, game):
        return

    from engine.phases.day import start_day
    await start_day(bus, game)
