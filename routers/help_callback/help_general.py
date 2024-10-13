from aiogram import F, Router
from aiogram.types import Message

router = Router(name = __name__)


@router.message(F.text == "info")
async def help_info(message: Message) -> None:
    answer: str = (
        f"You can get information about your role\n"
    )
    await message.answer(answer)


@router.message(F.text == "start")
async def help_register(message: Message) -> None:
    answer: str = (
        f"You can register into a game\n"
    )
    await message.answer(answer)


@router.message(F.text == "leave")
async def help_leave(message: Message) -> None:
    answer: str = (
        f"You can leave a game that has not been started yet\n"
    )
    await message.answer(answer)


@router.message(F.text == "list")
async def help_list(message: Message) -> None:
    answer: str = (
        f"You can see which players are still in the game\n"
    )
    await message.answer(answer)
