from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from internal import (
    ADMIN,
    bot,
    candidates,
    convert_username_to_id,
    forgive_players,
    kick_players,
    mafia_round,
    reset
)
from internal.player import Player

router = Router(name = __name__)


@router.message(Command('start_game'))
async def start_game_command(message: Message) -> None:
    user: str = message.from_user.username
    if user != ADMIN:
        await message.answer("Permission denied\n")
        return

    tmp = set(candidates)
    mafia_round.set_up(list(tmp))
    candidates.clear()
    await reset()

    mafia_team: list[int] = mafia_round.find_role("Mafia")
    mafia_info: str = "These guys are mafia:\n"
    for index in mafia_team:
        killer: Player = mafia_round.players[index]
        if killer.role == "Don":
            mafia_info += f"- {killer.tg_username}, Don\n"
        else:
            mafia_info += f"- {killer.tg_username}\n"

    roles: str = "In this game there are these roles:\n"
    for role in sorted(mafia_round.roles):
        roles += f"- {role}\n"

    for player in mafia_round.players:
        chat_id: int = convert_username_to_id[player.tg_username]
        await bot.send_message(chat_id = chat_id, text = player.role)
        await bot.send_message(chat_id = chat_id, text = roles)
        if player.role in ["Don", "Mafia"]:
            await bot.send_message(chat_id = chat_id, text = mafia_info)


@router.message(Command('allow'))
async def allow_voting_command(message: Message) -> None:
    user: str = message.from_user.username
    if user != ADMIN:
        await message.answer("Permission denied\n")
        return

    mafia_round.allowed_to_vote = True
    still_alive: list[int] = [convert_username_to_id[item] for item in mafia_round.find_alive()]

    answer: str = "You can vote now\n"
    for chat_id in still_alive:
        await bot.send_message(chat_id = chat_id, text = answer)


@router.message(Command('kick'))
async def kick_command(message: Message) -> None:
    user: str = message.from_user.username
    if user != ADMIN:
        await message.answer("Permission denied\n")
        return

    await kick_players()


@router.message(Command('forgive'))
async def forgive_command(message: Message) -> None:
    user: str = message.from_user.username
    if user != ADMIN:
        await message.answer("Permission denied\n")
        return

    await forgive_players()


@router.message(Command('night'))
async def set_night_command(message: Message) -> None:
    user: str = message.from_user.username
    if user != ADMIN:
        await message.answer("Permission denied\n")
        return

    mafia_round.state = 0
    mafia_round.allowed_to_vote = False

    alive: str = "These players are still alive:\n"
    still_alive: list[int] = []
    for player in mafia_round.players:
        if not player.alive:
            continue

        alive += f"- {player.tg_username}\n"
        still_alive.append(convert_username_to_id[player.tg_username])
        player.alibi = False
        player.muted = False

    answer: str = "It's night time\n"
    for chat_id in still_alive:
        await bot.send_message(chat_id = chat_id, text = answer)

    for player in mafia_round.players:
        if not player.alive or player.role == "Peace":
            continue

        await bot.send_message(chat_id = convert_username_to_id[player.tg_username],
                               text = alive)
