from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ErrorEvent, Message, TelegramObject
from loguru import logger

from src.bot.keyboard.inline import InlineKeyboard
from src.database import Database
from src.megafon.account import MegafonAccount
from src.megafon.datatypes import MegafonAccountData
from src.megafon.manager import MegafonManager


class LoadDataMiddleware(BaseMiddleware):
    async def get_user_megafon_managers(
        self, user_id: int | str
    ) -> list[MegafonManager]:
        db = Database()
        accounts = await db.get_accounts_by_owner_id(int(user_id))
        return [
            MegafonManager(MegafonAccount(MegafonAccountData(*account)))
            for account in accounts
        ]

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        elif isinstance(event, ErrorEvent):
            update = event.update
            user_id = (
                update.message.from_user.id
                if update.message
                else update.callback_query.from_user.id
            )
        else:
            logger.error("Не удалось определить id пользователя из события")
            raise Exception("Не удалось определить id пользователя из события")

        state: FSMContext | None = data.get("state")
        megafon_managers = await self.get_user_megafon_managers(user_id)

        data["state_data"] = await state.get_data() if state else {}
        data["database"] = Database()
        data["megafon_managers"] = megafon_managers
        data["keyboard"] = InlineKeyboard(megafon_managers)
        data["megafon_managers_dict"] = {
            manager.account.data.account_id: manager
            for manager in megafon_managers
        }
        return await handler(event, data)
