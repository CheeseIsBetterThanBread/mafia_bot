from os import environ

from aiogram import Bot

from internal.game import Game
from internal.player import Player

API_TOKEN: str = environ['MAFIA_API_TOKEN']
ADMIN: str = environ['MAFIA_ADMIN']

bot: Bot = Bot(token = API_TOKEN)

candidates: list[str] = []
convert_username_to_id: dict[str, int] = {}
mafia_round: Game = Game()

async def reset() -> None:
    mafia_round.state = -1
    mafia_round.allowed_to_vote = False

    mafia_round.important['mute'] = -1
    mafia_round.important['visit'] = -1
    mafia_round.important['kill'] = -1
    mafia_round.important['heal'] = -1
    mafia_round.important['maniac_kill'] = -1
    mafia_round.important['maniac_heal'] = -1
    mafia_round.important['check'] = -1
    mafia_round.important['don_check'] = -1

    usernames: list[str] = []
    for user in mafia_round.players:
        usernames.append(user.tg_username)

    for user in usernames:
        mafia_round.for_vote[user] = -1
        mafia_round.voted[user] = -1


async def end_night() -> None:
    still_alive: list[int] = []
    immortal: int = -1
    whore: int = -1
    for index in range(len(mafia_round.players)):
        user: Player = mafia_round.players[index]
        if not user.alive:
            continue

        still_alive.append(convert_username_to_id[user.tg_username])
        if user.role == "Tula":
            whore = index
        elif user.role == "Immortal":
            immortal = index

    answer: str = ""
    shot: list[int] = [mafia_round.important["kill"],
                       mafia_round.important["maniac_kill"]]
    healed: list[int] = [mafia_round.important["heal"],
                         mafia_round.important["maniac_heal"]]
    killed: list[int] = [item for item in shot if item >= 0 and item not in healed]

    client: int = mafia_round.important['visit']
    if whore != -1:
        if whore not in shot:
            if client in killed:
                killed.remove(client)
        elif client >= 0:
            if client not in killed:
                killed.append(client)

            if client in healed and client in killed:
                killed.remove(client)
            if whore in healed and whore in killed:
                killed.remove(whore)

    if immortal in killed:
        killed.remove(immortal)

    if len(killed) == 0:
        answer += f"Everyone survived this night\n"
    else:
        for corpse in killed:
            mafia_round.players[corpse].alive = False

            lost_role: str = mafia_round.players[corpse].role
            mafia_round.night_actions -= mafia_round.actions[lost_role]

            answer += f"{mafia_round.players[corpse].tg_username} did not survive\n"

    muted: str = ""
    for user in mafia_round.players:
        if user.alive and user.muted:
            muted += f"{user.tg_username} was muted\n"
    answer = muted + answer

    for chat_id in still_alive:
        await bot.send_message(chat_id = chat_id, text = answer)

    await reset()
    await check_for_endgame()


async def count_votes() -> None:
    victims: list[int] = []
    for _, victim_index in mafia_round.voted:
        victims.append(victim_index)

    unique: set[int] = set(victims)
    max_count: int = max(victims.count(item) for item in unique)
    mafia_round.kicked = [item for item in unique if victims.count(item) == max_count]

    if len(mafia_round.kicked) == 1:
        await kick_players()
        return

    answer: str = "There is a balance between players:\n"
    for index in mafia_round.kicked:
        answer += f"- {mafia_round.players[index].tg_username}\n"

    still_alive: list[int] = []
    for user in mafia_round.players:
        if not user.alive:
            continue

        still_alive.append(convert_username_to_id[user.tg_username])

    for chat_id in still_alive:
        await bot.send_message(chat_id = chat_id, text = answer)


async def kick_players() -> None:
    still_alive: list[int] = []
    for user in mafia_round.players:
        if not user.alive:
            continue

        still_alive.append(convert_username_to_id[user.tg_username])

    answer: str = f"Kicked out following players:\n"
    note: str = ""
    for index in mafia_round.kicked:
        if mafia_round.players[index].alibi:
            note += f"Player {mafia_round.players[index].tg_username} has an alibi\n"
            continue

        answer += f"- {mafia_round.players[index].tg_username}\n"
        mafia_round.players[index].alive = False

        lost_role: str = mafia_round.players[index].role
        mafia_round.night_actions -= mafia_round.actions[lost_role]

    answer = note + answer
    for chat_id in still_alive:
        await bot.send_message(chat_id = chat_id, text = answer)

    await check_for_endgame()


async def forgive_players() -> None:
    still_alive: list[int] = []
    for user in mafia_round.players:
        if not user.alive:
            continue

        still_alive.append(convert_username_to_id[user.tg_username])

    answer: str = "No one was kicked out\n"

    for chat_id in still_alive:
        await bot.send_message(chat_id = chat_id, text = answer)


async def check_for_endgame() -> None:
    mafia_counter: int = 0
    counter: int = 0
    maniac_alive: bool = False

    still_alive: list[int] = []
    for user in mafia_round.players:
        if not user.alive:
            continue

        still_alive.append(convert_username_to_id[user.tg_username])
        counter += 1
        if user.role in ["Mafia", "Don"]:
            mafia_counter += 1
        elif user.role == "Maniac":
            maniac_alive = True

    answer: str = ""
    if mafia_counter * 2 >= counter and not maniac_alive:
        answer += "Mafia won this round\n"
    elif not maniac_alive and mafia_counter == 0:
        answer += "Innocent people win\n"
    elif maniac_alive and counter == 2:
        answer += "Maniac wins\n"

    if len(answer) != 0:
        for chat_id in still_alive:
            await bot.send_message(chat_id = chat_id, text = answer)
