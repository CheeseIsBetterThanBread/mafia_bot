from aiogram import Router

from routers.help_callback.help_day import router as day_help_router
from routers.help_callback.help_general import router as entry_help_router
from routers.help_callback.help_night import router as night_help_router

router = Router(name = __name__)
router.include_routers(
    entry_help_router,
    day_help_router,
    night_help_router,
)
