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

    mafia_round.important['kill'] = -1
    mafia_round.important['heal'] = -1

    usernames: list[str] = []
    for user in mafia_round.players:
        usernames.append(user.tg_username)

    for user in usernames:
        mafia_round.for_vote[user] = -1
        mafia_round.voted[user] = -1


async def end_night() -> None:
    still_alive: list[int] = []
    for user in mafia_round.players:
        if not user.alive:
            continue

        still_alive.append(convert_username_to_id[user.tg_username])

    answer: str
    killed: int = mafia_round.important["kill"]
    if mafia_round.important["kill"] == mafia_round.important["heal"]:
        answer = f"Everyone survived this night\n"
    else:
        mafia_round.players[killed].alive = False
        if mafia_round.players[killed].role != "Peace":
            mafia_round.not_trivial -= 1

        answer = f"{mafia_round.players[killed].tg_username} did not survive\n"

    for chat_id in still_alive:
        await bot.send_message(chat_id = chat_id, text = answer)

    await reset()


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
    for index in mafia_round.kicked:
        answer += f"- {mafia_round.players[index].tg_username}\n"
        mafia_round.players[index].alive = False
        if mafia_round.players[index].role != "Peace":
            mafia_round.not_trivial -= 1

    for chat_id in still_alive:
        await bot.send_message(chat_id = chat_id, text = answer)


async def forgive_players() -> None:
    still_alive: list[int] = []
    for user in mafia_round.players:
        if not user.alive:
            continue

        still_alive.append(convert_username_to_id[user.tg_username])

    answer: str = "No one was kicked out\n"

    for chat_id in still_alive:
        await bot.send_message(chat_id = chat_id, text = answer)
