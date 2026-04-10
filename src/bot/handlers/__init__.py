from aiogram import Router

from .callback import router as callback_router
from .errors import router as error_router
from .message import router as message_router

main_router = Router()
main_router.include_routers(callback_router, message_router, error_router)
