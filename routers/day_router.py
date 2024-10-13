from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from internal import (
    count_votes,
    mafia_round
)

router = Router(name = __name__)


@router.message(Command('put_up'))
async def put_up_player_command(message: Message) -> None:
    user: str = message.from_user.username
    victim: str = message.text.split(' ')[1:][0][1:]

    user_index: int = mafia_round.find_user(user)
    if user_index == -1 or not mafia_round.players[user_index].alive:
        await message.answer("You can't put up players for vote\n")
        return

    if mafia_round.for_vote[user] != -1:
        await message.answer("You can't put up more than one person\n")
        return

    victim_index: int = mafia_round.find_user(victim)
    if victim_index == -1:
        await message.answer("This player does not exist\n")
        return

    mafia_round.for_vote[user] = victim_index
    await message.answer(f"You've put {victim} up for a vote\n")


@router.message(Command('display'))
async def display_victims_command(message: Message) -> None:
    user: str = message.from_user.username
    user_index: int = mafia_round.find_user(user)

    if user_index == -1:
        await message.answer("You are not in the game\n")
        return

    victims: list[int] = []
    for _, victim_index in mafia_round.for_vote:
        if victim_index == -1:
            continue

        victims.append(victim_index)

    victims: set[int] = set(victims)
    answer: str = "You can vote for these players:\n"
    for index in victims:
        answer += f"- {mafia_round.players[index].tg_username}\n"

    await message.answer(answer)


@router.message(Command('vote'))
async def vote_player(message: Message) -> None:
    if not mafia_round.allowed_to_vote:
        await message.answer("You can't vote yet\n")
        return

    user: str = message.from_user.username
    victim: str = message.text.split(' ')[1:][0][1:]

    if mafia_round.voted[user] != -1:
        await message.answer("You've already voted\n")
        return

    user_index: int = mafia_round.find_user(user)
    if user_index == -1 or not mafia_round.players[user_index].alive:
        await message.answer("You can't vote\n")
        return

    victims: set[int] = set()
    for person, victim_index in mafia_round.for_vote:
        victims.add(victim_index)

    victim_index: int = mafia_round.find_user(victim)
    if victim_index == -1 or not victim_index in victims:
        await message.answer("You can't vote for that player\n")
        return

    mafia_round.voted[user] = victim_index
    await message.answer(f"You've voted for {victim}\n")

    counter: int = 0
    for _, victim_index in mafia_round.voted:
        if victim_index != -1:
            counter += 1

    alive: int = 0
    for participant in mafia_round.players:
        if participant.alive:
            alive += 1

    if counter == alive:
        await count_votes()
