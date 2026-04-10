import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

from src.bot.handlers import main_router
from src.bot.middlewares import (
    AccountActionsLoggerMiddleware,
    AutoAnswerCallbackMiddleware,
    LoadDataMiddleware,
)


async def start_telegram_bot() -> None:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN не установлен")

    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(LoadDataMiddleware())
    dp.callback_query.middleware(LoadDataMiddleware())
    dp.errors.middleware(LoadDataMiddleware())
    dp.callback_query.outer_middleware(AutoAnswerCallbackMiddleware())
    dp.callback_query.middleware(AccountActionsLoggerMiddleware())
    dp.include_router(main_router)

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот запущен")
    await dp.start_polling(bot)
