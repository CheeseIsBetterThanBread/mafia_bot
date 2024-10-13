from aiogram import Router

from routers.day_router import router as day_router
from routers.general_router import router as general_router
from routers.help_callback import router as help_router
from routers.night_router import router as night_router

router = Router(name = __name__)
router.include_routers(
    day_router,
    help_router,
    night_router,
)

# Because general_router contains fallback
router.include_router(general_router)
