from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject
from loguru import logger

from src.bot.filters.callback_data import AccountsCallbackData


class AccountActionsLoggerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        callback_data: str = data.get("callback_data", "")

        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        if not isinstance(callback_data, AccountsCallbackData):
            return await handler(event, data)

        with logger.contextualize(account_id=callback_data.account_id):
            await handler(event, data)
