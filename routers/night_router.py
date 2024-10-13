from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from internal import (
    end_night,
    mafia_round
)

router = Router(name = __name__)


@router.message(Command('kill'))
async def kill_player_command(message: Message) -> None:
    if mafia_round.state == -1:
        await message.answer("You have to wait for the night\n")
        return

    user: str = message.from_user.username
    dead_man: str = message.text.split(' ')[1:][0][1:]

    mafia: int = mafia_round.find_user(user)
    if mafia == -1 or mafia_round.players[mafia].role != "Mafia":
        await message.answer("You have no rights here\n")
        return

    dead: int = mafia_round.find_user(dead_man)
    if dead == -1:
        await message.answer("This player does not exist\n")
        return
    if not mafia_round.players[dead].alive:
        await message.answer("Come on, don't shoot a corpse :(\n")
        return

    if mafia_round.important['kill'] != -1:
        await message.answer(
            f"You can't change your choice\n"
            f"You've already chosen {dead_man}\n"
        )
        return

    mafia_round.important['kill'] = dead
    mafia_round.state += 1

    await message.answer(f"You've shot {dead_man}\n")

    if mafia_round.state == mafia_round.not_trivial:
        await end_night()


@router.message(Command('heal'))
async def heal_player_command(message: Message) -> None:
    if mafia_round.state == -1:
        await message.answer("You have to wait for the night\n")
        return

    user: str = message.from_user.username
    healed_man: str = message.text.split(' ')[1:][0][1:]

    doctor: int = mafia_round.find_user(user)
    if doctor == -1 or mafia_round.players[doctor].role != "Doctor":
        await message.answer("You have no rights here\n")
        return

    healed: int = mafia_round.find_user(healed_man)
    if healed == -1:
        await message.answer("This player does not exist\n")
        return
    if not mafia_round.players[healed].alive:
        await message.answer("You are not that good to bring back the dead\n")
        return
    if healed == mafia_round.last_healed:
        await message.answer("You can't heal player twice in a row\n")
        return

    if mafia_round.important['heal'] != -1:
        await message.answer(
            f"You can't change your choice\n"
            f"You've already chosen {healed_man}\n"
        )
        return

    mafia_round.important['heal'] = healed
    mafia_round.last_healed = healed
    mafia_round.state += 1

    await message.answer(f"You've healed {healed_man}")

    if mafia_round.state == mafia_round.not_trivial:
        await end_night()


@router.message(Command('check'))
async def check_player_command(message: Message) -> None:
    if mafia_round.state == -1:
        await message.answer("You have to wait for the night\n")
        return

    user: str = message.from_user.username
    suspicious_man: str = message.text.split(' ')[1:][0][1:]

    sheriff: int = mafia_round.find_user(user)
    if sheriff == -1 or mafia_round.players[sheriff].role != "Sheriff":
        await message.answer("You have no rights here\n")
        return

    checked: int = mafia_round.find_user(suspicious_man)
    if checked == -1:
        await message.answer("This player does not exist\n")
        return
    if not mafia_round.players[checked].alive:
        await message.answer("Sorry, dead men tell no tales\n")
        return

    if mafia_round.players[checked].role == "Mafia":
        await message.answer("That's mafia\n")
    else:
        await message.answer("He's innocent\n")

    mafia_round.state += 1
    if mafia_round.state == mafia_round.not_trivial:
        await end_night()
