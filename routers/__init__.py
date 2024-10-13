from aiogram import Router

from routers.admin_router import router as admin_router
from routers.day_router import router as day_router
from routers.general_router import router as general_router
from routers.help_callback import router as help_router
from routers.night_router import router as night_router

router = Router(name = __name__)
router.include_routers(
    admin_router,
    day_router,
    help_router,
    night_router,
)

# Because general_router contains fallback
router.include_router(general_router)
