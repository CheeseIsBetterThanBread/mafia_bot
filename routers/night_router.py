from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from internal import (
    end_night,
    mafia_round
)
from internal.player import Player

router = Router(name = __name__)


async def check_for_access(message: Message, available_roles: list[str]) -> int:
    user: str = message.from_user.username
    index: int = mafia_round.find_user(user)

    if index == -1 or mafia_round.players[index].role not in available_roles:
        await message.answer("You have no rights here\n")
        return -1

    if not mafia_round.players[index].alive:
        await message.answer("You have to be alive to do this action\n")
        return -1

    return index


async def find_recipient(message: Message, user: str) -> int:
    recipient: int = mafia_round.find_user(user)

    if recipient == -1:
        await message.answer("This player does not exist\n")
        return -1

    if not mafia_round.players[recipient].alive:
        await message.answer("Player has to be alive\n")
        return -1

    return recipient


async def already_chosen(message: Message, key: str) -> bool:
    if mafia_round.important[key] != -1:
        player: str = mafia_round.players[mafia_round.important[key]].tg_username
        await message.answer(
            f"You can't change your choice\n"
            f"You've already chosen {player}\n"
        )
        return True
    return False


async def already_muted(message: Message, key: str) -> bool:
    if mafia_round.important[key] != -1:
        await message.answer("Will you chill already? You are muted\n")
        return True
    return False


@router.message(Command('kill'))
async def kill_player_command(message: Message) -> None:
    if mafia_round.state == -1:
        await message.answer("You have to wait for the night\n")
        return

    dead_man: str = message.text.split(' ')[1:][0][1:]

    killer: int = await check_for_access(message, ["Mafia", "Don", "Maniac"])
    if killer == -1:
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
    role: str = mafia_round.players[killer].role

    thieves: list[int] = mafia_round.find_role("Thief")
    if len(thieves) != 0 and mafia_round.important['mute'] == -1:
        await message.answer("Sorry, have to wait for the thief")
        return
    elif len(thieves) != 0 and role == mafia_round.muted_group == "Maniac":
        if await already_muted(message, 'maniac_kill'):
            return

        mafia_round.important['maniac_kill'] = -2
        mafia_round.important['maniac_heal'] = -2
        mafia_round.last_maniac = "maniac_kill"
        mafia_round.state += 1

        await message.answer("Sorry, you've been muted\n")
        if mafia_round.state == mafia_round.night_actions:
            await end_night()
        return
    elif len(thieves) != 0 and role in ["Don", "Mafia"] and mafia_round.muted_group == "Mafia":
        if await already_muted(message, 'kill'):
            return

        mafia_round.important['kill'] = -2
        mafia: list[int] = mafia_round.find_role("Mafia")
        mafia_round.state += len(mafia)

        await message.answer("Sorry, you've been muted\n")
        if mafia_round.state == mafia_round.night_actions:
            await end_night()
        return

    dead: int = await find_recipient(message, dead_man)

    if mafia_round.players[killer].role != "Maniac":
        if await already_chosen(message, 'kill'):
            return

        mafia = mafia_round.find_role('Mafia')
        mafia_round.important['kill'] = dead
        mafia_round.state += len(mafia)

        await message.answer(f"You've shot {dead_man}\n")
    else:
        if await already_chosen(message, 'maniac_kill'):
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

    healer: int = await check_for_access(message, ["Doctor", "Maniac"])
    if healer == -1:
        return

    thieves: list[int] = mafia_round.find_role("Thief")
    if len(thieves) != 0 and mafia_round.important['mute'] == -1:
        await message.answer("Sorry, have to wait for the thief")
        return
    elif len(thieves) != 0 and mafia_round.muted_group == mafia_round.players[healer].role:
        role: str = mafia_round.muted_group
        if role == "Maniac":
            if await already_muted(message, 'maniac_heal'):
                return

            mafia_round.important['maniac_kill'] = -2
            mafia_round.important['maniac_heal'] = -2
            mafia_round.last_maniac = "maniac_kill"
        else:
            if await already_muted(message, 'heal'):
                return

            mafia_round.important['heal'] = -2
            mafia_round.last_healed = -1

        mafia_round.state += 1

        await message.answer("Sorry, you were muted\n")
        if mafia_round.state == mafia_round.night_actions:
            await end_night()
        return

    if mafia_round.players[healer].role == "Maniac":
        if mafia_round.last_maniac == "maniac_heal":
            await message.answer("You can't heal yourself twice in a row\n")
            return

        mafia_round.important['maniac_heal'] = healer
        mafia_round.last_maniac = "maniac_heal"
        mafia_round.state += 1

        await message.answer("You've healed yourself\n")
        if mafia_round.state == mafia_round.night_actions:
            await end_night()
        return


    healed_man: str = message.text.split(' ')[1:][0][1:]
    healed: int = await find_recipient(message, healed_man)
    if healed == -1:
        return
    if healed == mafia_round.last_healed:
        await message.answer("You can't heal player twice in a row\n")
        return

    if await already_chosen(message, 'heal'):
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

    suspicious_man: str = message.text.split(' ')[1:][0][1:]

    checker: int = await check_for_access(message, ["Sheriff", "Don"])
    if checker == -1:
        return

    thieves: list[int] = mafia_round.find_role("Thief")
    if len(thieves) != 0 and mafia_round.important['mute'] == -1:
        await message.answer("Sorry, have to wait for the thief")
        return
    elif len(thieves) != 0 and mafia_round.muted_group == mafia_round.players[checker].role:
        if mafia_round.muted_group == "Sheriff":
            if await already_muted(message, 'check'):
                return
            mafia_round.important['check'] = -2
        else:
            if await already_muted(message, 'don_check'):
                return
            mafia_round.important['don_check'] = -2

        mafia_round.state += 1
        await message.answer("Sorry, you were muted\n")

        if mafia_round.state == mafia_round.night_actions:
            await end_night()
        return

    checked: int = await find_recipient(message, suspicious_man)
    if checked == -1:
        return

    role: str = mafia_round.players[checker].role
    if role == "Sheriff" and await already_chosen(message, 'check'):
        return
    elif role == "Don" and await already_chosen(message, 'don_check'):
        return

    if mafia_round.players[checked].role in ["Mafia", "Don"] and role == "Sheriff":
        await message.answer("That's mafia\n")
        mafia_round.important['check'] = checked
    elif role == "Sheriff":
        await message.answer("He's innocent\n")
        mafia_round.important['check'] = checked
    elif mafia_round.players[checked].role == "Sheriff":
        await message.answer("That's sheriff\n")
        mafia_round.important['don_check'] = checked
    else:
        await message.answer("Some random guy\n")
        mafia_round.important['don_check'] = checked

    mafia_round.state += 1
    await message.answer(f"You've checked {suspicious_man}\n")
    if mafia_round.state == mafia_round.night_actions:
        await end_night()


@router.message(Command('visit'))
async def visit_command(message: Message) -> None:
    if mafia_round.state == -1:
        await message.answer("You have to wait for the night\n")
        return

    weird_man: str = message.text.split(' ')[1:][0][1:]

    whore: int = await check_for_access(message, ["Tula"])
    if whore == -1:
        return

    thieves: list[int] = mafia_round.find_role("Thief")
    if len(thieves) != 0 and mafia_round.important['mute'] == -1:
        await message.answer("Sorry, have to wait for the thief")
        return
    elif len(thieves) != 0 and mafia_round.muted_group == mafia_round.players[whore].role:
        if await already_muted(message, 'visit'):
            return

        mafia_round.state += 1
        mafia_round.last_visited = -1
        mafia_round.important['visit'] = -2

        await message.answer("Sorry, you were muted\n")
        if mafia_round.state == mafia_round.night_actions:
            await end_night()
        return

    visited: int = await find_recipient(message, weird_man)
    if visited == -1:
        return
    if visited == mafia_round.last_visited:
        await message.answer("You can't visit player twice in a row\n")
        return

    if await already_chosen(message, 'visit'):
        return

    mafia_round.important['visit'] = visited
    mafia_round.last_visited = visited
    mafia_round.players[visited].alibi = True
    mafia_round.state += 1

    await message.answer(f"You've visited {weird_man}\n")
    if mafia_round.state == mafia_round.night_actions:
        await end_night()


@router.message(Command('mute'))
async def mute_command(message: Message) -> None:
    if mafia_round.state == -1:
        await message.answer("You have to wait for the night\n")
        return

    robbed_man: str = message.text.split(' ')[1:][0][1:]

    thief: int = await check_for_access(message, ["Thief"])
    if thief == -1:
        return

    robbed: int = await find_recipient(message, robbed_man)
    if robbed == -1:
        return
    if robbed == mafia_round.last_robbed:
        await message.answer("You can't mute one player for two nights in a row\n")
        return

    if await already_chosen(message, 'mute'):
        return

    mafia_round.important['mute'] = robbed
    mafia_round.last_robbed = robbed
    mafia_round.players[robbed].muted = True
    mafia_round.muted_group = mafia_round.players[robbed].role
    mafia_round.state += 1

    await message.answer(f"You've muted {robbed_man}\n")
    if mafia_round.state == mafia_round.night_actions:
        await end_night()
