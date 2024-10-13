from aiogram import F, Router
from aiogram.types import Message

router = Router(name = __name__)


@router.message(F.text == "put_up")
async def help_put_up(message: Message) -> None:
    answer: str = (
        f"This command allows you to put players up for vote\n"
        f"You can't put up more than one player, also you can't change your decision\n"
    )
    await message.answer(answer)


@router.message(F.text == "vote")
async def help_vote(message: Message) -> None:
    answer: str = (
        f"This command allows you to vote for players\n"
        f"You can't vote for more than one player, "
        f"also you can't vote for players that are not up for vote\n"
        f"You can't vote until all speeches have been heard\n"
    )
    await message.answer(answer)


@router.message(F.text == "display")
async def help_display(message: Message) -> None:
    answer: str = (
        f"With this command you can see all players, that are up fro vote right now\n"
    )
    await message.answer(answer)
