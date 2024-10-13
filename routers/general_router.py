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
    user_id: int = message.from_user.id

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
