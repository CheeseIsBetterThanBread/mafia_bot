from pyexpat.errors import messages

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from internal import (
    ADMIN,
    bot,
    candidates,
    convert_username_to_id, mafia_round
)
from keyboards.help_keyboard import build_help_keyboard

router = Router(name = __name__)


@router.message(Command('start'))
async def start_command(message: Message) -> None:
    user: str = message.from_user.username
    user_id: int = message.from_user.id
    convert_username_to_id[user] = user_id

    await message.answer(f"Hi, {user}, you can see my commands with /help\n")


@router.message(Command('register'))
async def register_command(message: Message) -> None:
    user: str = message.from_user.username
    if user in candidates:
        await message.answer("You've already registered\n")
        return

    candidates.append(user)
    await message.answer("You've registered\n")

    notification: str = f"Player {user} joined the game\n"
    await bot.send_message(chat_id = convert_username_to_id[ADMIN],
                           text = notification)


@router.message(Command('info'))
async def info_command(message: Message) -> None:
    user: str = message.from_user.username
    index: int = mafia_round.find_user(user)
    if index == -1:
        await message.answer("You have no role\n")
        return

    role: str = mafia_round.players[index].role
    answer: str = ""
    if role == "Mafia":
        answer += (
            f"You can shoot one person per night. "
            f"If don is present, he should make the final decision\n"
            f"You win if you have at least n teammates on the table with 2n people "
            f"and maniac is dead"
        )
    elif role == "Don":
        answer += (
            f"You are the leader of the Mafia. "
            f"Apart from regular killing action, you can look for sheriff in the crowd\n"
            f"You win if and only if mafia wins"
        )
    elif role == "Maniac":
        answer += (
            f"You can shoot one person per night or heal yourself, "
            f"but you can't heal yourself twice in a row\n"
            f"You win if you are left with only one person at a table"
        )
    elif role == "Sheriff":
        answer += (
            f"You can look for mafia every night\n"
            f"You win when innocent people win"
        )
    elif role == "Doctor":
        answer += (
            f"You can heal one person per night, "
            f"but you can't choose the same player twice in a row\n"
            f"You win when innocent people win"
        )
    elif role == "Tula":
        answer += (
            f"You can visit one player per night, "
            f"but you can't choose the same player twice in a row\n"
            f"If you visit a player that has been shot, you heal him\n"
            f"If you are shot, you both are dead, unless someone heals you\n"
            f"Your client gets immunity for the next day, "
            f"i.e. he cannot be kicked of by voting\n"
            f"You win when innocent people win"
        )
    elif role == "Thief":
        answer += (
            f"You can mute one person per night, "
            f"but you can't choose the same player twice in a row\n"
            f"Muted player cannot use his actions during the night, "
            f"also he cannot speak during the following day\n"
            f"You win when innocent people win"
        )
    elif role == "Immortal":
        answer += (
            f"You are just like regular peaceful player "
            f"except for the fact that you can't die during the night\n"
            f"You win when innocent people win"
        )
    elif role == "Peace":
        answer += (
            f"You are regular citizen. Good luck dealing with that bs\n"
            f"You win when innocent people win"
        )
    else:
        answer += (
            f"Something went wrong\n"
            f"Please, tell admin that you've got role {role}"
        )
    await message.answer(answer)

@router.message(Command('register'))
async def register_command(message: Message) -> None:
    user: str = message.from_user.username

    if user in candidates:
        await message.answer("You've already registered\n")
        return

    candidates.append(user)
    await message.answer("You've registered\n")

    notification: str = f"Player {user} joined the game\n"
    await bot.send_message(chat_id = convert_username_to_id[ADMIN],
                           text = notification)


@router.message(Command('leave'))
async def leave_command(message: Message) -> None:
    if len(candidates) == 0:
        await message.answer("You can't leave now\n")
        return

    user: str = message.from_user.username
    if candidates.count(user) != 0:
        candidates.remove(user)

        notification: str = f"Player {user} left the game\n"
        await bot.send_message(chat_id = convert_username_to_id[ADMIN],
                               text = notification)

    await message.answer("You've left the round\n")



@router.message(Command('list'))
async def list_command(message: Message) -> None:
    answer: str = "These players are still alive:\n"
    for user in mafia_round.players:
        if not user.alive:
            continue

        answer += f"- {user.tg_username}\n"

    await message.answer(answer)


@router.message(Command('help'))
async def help_command(message: Message) -> None:
    answer: str = "Which command are you interested in?"
    markup = build_help_keyboard()

    await message.answer(answer, reply_markup = markup)


@router.message()
async def default_response(message: Message) -> None:
    answer: str = (
        f"Sorry, I don't know this command\n"
        f"For more information check out /help\n"
    )
    await message.answer(answer)
