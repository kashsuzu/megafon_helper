from aiogram import Router, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types.error_event import ErrorEvent
from loguru import logger

from src.bot.fsm.add_account import AddAccountStates
from src.bot.keyboard.inline import InlineKeyboard
from src.megafon.manager import MegafonManager

router = Router()


@router.error(StateFilter(AddAccountStates))
async def catch_add_account_error(
    event: ErrorEvent,
    state: FSMContext,
    keyboard: InlineKeyboard,
    state_data: dict,
):
    megafon_manager: MegafonManager = state_data["megafon_manager"]
    update = event.update
    text = html.bold(
        "Произошла ошибка во время добавления аккаунта. " \
        "Обратитесь к разработчику или посмотрите логи.\n❌ Ошибка:\n"
    ) + html.blockquote(f"{event.exception}")

    logger.error(
        f"Возникла ошибка во время добавления аккаунта:\n{event.exception}"
    )

    try:
        if update.message:
            await update.message.answer(
                text=text, reply_markup=keyboard.menu()
            )
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.answer(
                text=text, reply_markup=keyboard.menu()
            )
    except TelegramBadRequest as err:
        logger.warning(f"Не удалось отправить сообщение об ошибке:\n{err}")

    await megafon_manager.account.delete()
    await state.clear()


@router.error()
async def global_error_handler(
    event: ErrorEvent,
    keyboard: InlineKeyboard,
) -> None:
    logger.error(f"Возникла ошибка во время работы бота:\n{event.exception}")
    update = event.update
    text = html.bold(
        "Произошла ошибка. Обратитесь к разработчику или посмотрите логи.\n❌ Ошибка:\n"
    ) + html.blockquote(f"{event.exception}")
    
    try:
        if update.message:
            await update.message.answer(
                text=text, reply_markup=keyboard.menu()
            )
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.edit_text(
                text=text, reply_markup=keyboard.menu()
            )
    except TelegramBadRequest as err:
        logger.warning(f"Не удалось отправить сообщение об ошибке:\n{err}")
