from multiprocessing.connection import Connection

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

    killer: int = mafia_round.find_user(user)
    if killer == -1 or mafia_round.players[killer].role not in ["Mafia", "Don", "Maniac"]:
        await message.answer("You have no rights here\n")
        return
    if not mafia_round.players[killer].alive:
        await message.answer("Corpses can't kill\n")
        return
    if "Don" in mafia_round.roles and mafia_round.players[killer].role == "Mafia":
        don_index: int = 0
        for index in range(len(mafia_round.players)):
            if mafia_round.players[index].role == "Don":
                don_index = index
                break

        if mafia_round.players[don_index].alive:
            await message.answer("Only don can make this decision\n")
            return

    dead: int = mafia_round.find_user(dead_man)
    if dead == -1:
        await message.answer("This player does not exist\n")
        return
    if not mafia_round.players[dead].alive:
        await message.answer("Come on, don't shoot a corpse :(\n")
        return

    if mafia_round.players[killer].role != "Maniac":
        if mafia_round.important['kill'] != -1:
            player: str = mafia_round.players[mafia_round.important['kill']].tg_username
            await message.answer(
                f"You can't change your choice\n"
                f"You've already chosen {player}\n"
            )
            return

        counter: int = 0
        for participant in mafia_round.players:
            if participant.alive and participant.role in ["Mafia", "Don"]:
                counter += 1

        mafia_round.important['kill'] = dead
        mafia_round.state += counter

        await message.answer(f"You've shot {dead_man}\n")
    else:
        if mafia_round.important['maniac_kill'] != -1:
            player: str = mafia_round.players[mafia_round.important['maniac_kill']].tg_username
            await message.answer(
                f"You can't change your choice\n"
                f"You've already chosen {player}\n"
            )
            return

        mafia_round.important['maniac_kill'] = dead
        mafia_round.last_maniac = "maniac_kill"
        mafia_round.state += 1

        await message.answer(f"You've shot {dead_man}\n")

    if mafia_round.state == mafia_round.night_actions:
        await end_night()


@router.message(Command('heal'))
async def heal_player_command(message: Message) -> None:
    if mafia_round.state == -1:
        await message.answer("You have to wait for the night\n")
        return

    user: str = message.from_user.username

    healer: int = mafia_round.find_user(user)
    if healer == -1 or mafia_round.players[healer].role not in ["Doctor", "Maniac"]:
        await message.answer("You have no rights here\n")
        return
    if not mafia_round.players[healer].alive:
        await message.answer("How can you heal others if you couldn't even heal yourself?\n")
        return

    if mafia_round.players[healer].role == "Maniac":
        if mafia_round.last_maniac == "maniac_heal":
            await message.answer("You can't heal yourself twice in a row\n")
            return

        mafia_round.important['maniac_heal'] = healer
        mafia_round.last_maniac = "maniac_heal"
        mafia_round.state += 1

        await message.answer("You've healed yourself\n")
        return


    healed_man: str = message.text.split(' ')[1:][0][1:]
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
        player: str = mafia_round.players[mafia_round.important['heal']].tg_username
        await message.answer(
            f"You can't change your choice\n"
            f"You've already chosen {player}\n"
        )
        return

    mafia_round.important['heal'] = healed
    mafia_round.last_healed = healed
    mafia_round.state += 1

    await message.answer(f"You've healed {healed_man}")

    if mafia_round.state == mafia_round.night_actions:
        await end_night()


@router.message(Command('check'))
async def check_player_command(message: Message) -> None:
    if mafia_round.state == -1:
        await message.answer("You have to wait for the night\n")
        return

    user: str = message.from_user.username
    suspicious_man: str = message.text.split(' ')[1:][0][1:]

    checker: int = mafia_round.find_user(user)
    if checker == -1 or mafia_round.players[checker].role not in ["Sheriff", "Don"]:
        await message.answer("You have no rights here\n")
        return
    if not mafia_round.players[checker].alive:
        await message.answer("There is no way for you to check someone from 6ft under\n")
        return

    checked: int = mafia_round.find_user(suspicious_man)
    if checked == -1:
        await message.answer("This player does not exist\n")
        return
    if not mafia_round.players[checked].alive:
        await message.answer("Sorry, dead men tell no tales\n")
        return

    if mafia_round.players[checked].role == "Mafia" and mafia_round.players[checker].role == "Sheriff":
        await message.answer("That's mafia\n")
    elif mafia_round.players[checker].role == "Sheriff":
        await message.answer("He's innocent\n")
    elif mafia_round.players[checked].role == "Sheriff":
        await message.answer("That's sheriff\n")
    else:
        await message.answer("Some random guy\n")

    mafia_round.state += 1
    if mafia_round.state == mafia_round.night_actions:
        await end_night()


@router.message(Command('visit'))
async def visit_command(message: Message) -> None:
    if mafia_round.state == -1:
        await message.answer("You have to wait for the night\n")
        return

    user: str = message.from_user.username
    weird_man: str = message.text.split(' ')[1:][0][1:]

    whore: int = mafia_round.find_user(user)
    if whore == -1 or mafia_round.players[whore].role not in ["Tula"]:
        await message.answer("You have no rights here\n")
        return
    if not mafia_round.players[whore].alive:
        await message.answer("No one will accept your services\n")
        return

    visited: int = mafia_round.find_user(weird_man)
    if visited == -1:
        await message.answer("This player does not exist\n")
        return
    if not mafia_round.players[visited].alive:
        await message.answer("You have pretty weird taste in clients, that is not allowed\n")
        return
    if visited == mafia_round.last_visited:
        await message.answer("You can't visit player twice in a row\n")
        return

    if mafia_round.important['visit'] != -1:
        player: str = mafia_round.players[mafia_round.important['visit']].tg_username
        await message.answer(
            f"You can't change your choice\n"
            f"You've already chosen {player}\n"
        )
        return

    mafia_round.important['visit'] = visited
    mafia_round.last_visited = visited
    mafia_round.players[visited].alibi = True
    mafia_round.state += 1

    if mafia_round.state == mafia_round.night_actions:
        await end_night()
