from aiogram import F, Router
from aiogram.types import Message

router = Router(name = __name__)


@router.message(F.text == "kill")
async def help_kill(message: Message) -> None:
    answer: str = (
        f"This command can be used by mafia during the night time\n"
        f"Once victim is chosen, you can't change your mind\n"
        f"You can't kill someone, who is already dead\n"
    )
    await message.answer(answer)


@router.message(F.text == "heal")
async def help_heal(message: Message) -> None:
    answer: str = (
        f"This command can be used by doctor during the night time\n"
        f"You can't change your mind after you use it\n"
        f"You can't heal dead people or the same person twice in a row\n"
    )
    await message.answer(answer)


@router.message(F.text == "check")
async def help_check(message: Message) -> None:
    answer: str = (
        f"This command can be used by sheriff during the night time\n"
        f"You can't check dead people\n"
    )
    await message.answer(answer)
